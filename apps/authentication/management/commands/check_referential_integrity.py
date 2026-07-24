"""
Audit des références cross-service (order_type/order_id) de la base
`default` vers les commandes des bases delivery_db/market_db/marketplace_db.

Dans cette architecture "fake microservices", ces références ne sont que des
IntegerField bruts (voir config/database_router.py) : aucune contrainte de
base de données n'empêche une référence orpheline (commande supprimée ou
jamais créée). Cette commande est le seul filet de sécurité disponible.

Usage: python manage.py check_referential_integrity
"""
from django.core.management.base import BaseCommand
from django.db.models import F

from apps.authentication.services import _order_dispatch


class Command(BaseCommand):
    help = "Vérifie que les références order_type/order_id sont toutes valides."

    def handle(self, *args, **options):
        from apps.authentication.models import Notification, Conversation, LivreurPosition, PromoRedemption

        dispatch = _order_dispatch()
        orphans = []

        orphans += self._check(
            'Notification',
            Notification.objects.using('default').exclude(order_type='').values('id', 'order_type', 'order_id'),
            dispatch,
        )
        orphans += self._check(
            'Conversation',
            Conversation.objects.using('default').values('id', 'order_type', 'order_id'),
            dispatch,
        )
        orphans += self._check(
            'LivreurPosition',
            LivreurPosition.objects.using('default')
                .exclude(current_order_type='').exclude(current_order_id=None)
                .annotate(order_type=F('current_order_type'), order_id=F('current_order_id'))
                .values('id', 'order_type', 'order_id'),
            dispatch,
        )
        orphans += self._check(
            'PromoRedemption',
            PromoRedemption.objects.using('default').values('id', 'order_type', 'order_id'),
            dispatch,
        )

        if not orphans:
            self.stdout.write(self.style.SUCCESS('Aucune référence orpheline détectée.'))
            return

        self.stdout.write(self.style.ERROR(f'{len(orphans)} référence(s) orpheline(s) détectée(s) :'))
        for line in orphans:
            self.stdout.write(f'  - {line}')

    def _check(self, label, rows, dispatch):
        orphans = []
        for row in rows:
            order_type, order_id, row_id = row['order_type'], row['order_id'], row['id']

            if order_type not in dispatch:
                orphans.append(f"{label}#{row_id} : order_type '{order_type}' inconnu")
                continue

            db_alias, model, _ = dispatch[order_type]
            if not model.objects.using(db_alias).filter(id=order_id).exists():
                orphans.append(f"{label}#{row_id} : {order_type}#{order_id} introuvable dans {db_alias}")
        return orphans
