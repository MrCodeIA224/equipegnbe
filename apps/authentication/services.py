"""
Logique métier partagée entre apps (authentication étant la base `default`,
c'est le point d'entrée naturel pour tout ce qui est cross-service : codes
promo, adresses...).

Les lectures ci-dessous utilisent `.using('default')` explicitement : c'est
autorisé par le routeur (voir config/database_router.py) qui n'interdit que
les jointures ORM entre modèles de bases différentes, pas les requêtes
simples. delivery/market/marketplace peuvent donc importer cette fonction
directement sans que ça pose de problème de routage.
"""
from decimal import Decimal

from django.utils import timezone
from rest_framework import serializers

from .models import PromoCode, PromoRedemption, LivreurPosition, Notification, Conversation, OTPCode


def validate_and_apply_promo(code, user, order_type, subtotal):
    """
    Valide un code promo pour un utilisateur/type de commande/sous-total donnés.
    Ne modifie rien (pas d'effet de bord) : appelable en preview comme en
    validation finale. Lève ValidationError si invalide, sinon retourne
    {'promo': PromoCode, 'discount_amount': Decimal}.
    """
    subtotal = Decimal(subtotal)

    try:
        promo = PromoCode.objects.using('default').get(code__iexact=code, is_active=True)
    except PromoCode.DoesNotExist:
        raise serializers.ValidationError({'promo_code': 'Code promo invalide ou inactif.'})

    if promo.expiry_date and promo.expiry_date < timezone.now():
        raise serializers.ValidationError({'promo_code': 'Ce code promo a expiré.'})

    if promo.usage_limit is not None and promo.times_used >= promo.usage_limit:
        raise serializers.ValidationError({'promo_code': 'Ce code promo a atteint sa limite d\'utilisation.'})

    if promo.applicable_order_types and order_type not in promo.applicable_order_types:
        raise serializers.ValidationError({'promo_code': 'Ce code promo ne s\'applique pas à ce type de commande.'})

    if subtotal < promo.min_order_amount:
        raise serializers.ValidationError({
            'promo_code': f'Montant minimum de commande requis : {promo.min_order_amount:.0f} GNF.'
        })

    already_used = PromoRedemption.objects.using('default').filter(
        promo_code=promo, user_id=user.id
    ).exists()
    if already_used:
        raise serializers.ValidationError({'promo_code': 'Vous avez déjà utilisé ce code promo.'})

    if promo.discount_type == PromoCode.DiscountType.PERCENTAGE:
        discount_amount = subtotal * (promo.value / Decimal(100))
    else:
        discount_amount = promo.value
    discount_amount = min(discount_amount, subtotal)

    return {'promo': promo, 'discount_amount': discount_amount}


def redeem_promo(promo, user, order_type, order_id, discount_amount):
    """Enregistre l'utilisation d'un code promo (à appeler uniquement après
    création réussie de la commande, jamais lors d'une simple preview)."""
    from django.db.models import F

    PromoRedemption.objects.using('default').create(
        promo_code=promo, user=user, order_type=order_type,
        order_id=order_id, discount_amount=discount_amount,
    )
    PromoCode.objects.using('default').filter(id=promo.id).update(times_used=F('times_used') + 1)


def get_livreur_position(livreur_id):
    """
    Retourne la dernière position connue d'un livreur, ou None. Appelée depuis
    les actions `livreur_position` des viewsets delivery/market/marketplace,
    qui gèrent déjà la permission via leur propre get_queryset() scopé par rôle
    - cette fonction ne fait donc aucune vérification de permission elle-même.
    """
    try:
        position = LivreurPosition.objects.using('default').get(livreur_id=livreur_id)
    except LivreurPosition.DoesNotExist:
        return None
    return {
        'latitude': position.latitude,
        'longitude': position.longitude,
        'updated_at': position.updated_at,
    }


def notify(user_id, title, message, notification_type='SYSTEM', order_type='', order_id=None):
    """
    Crée une notification in-app pour un utilisateur. Import direct depuis
    delivery/market/marketplace views.py après une mutation existante - ne
    restructure jamais la machine à états, se contente d'informer.
    """
    Notification.objects.using('default').create(
        recipient_id=user_id, title=title, message=message,
        notification_type=notification_type, order_type=order_type, order_id=order_id,
    )


def consume_otp(user, purpose, code):
    """
    Valide le dernier code OTP actif d'un utilisateur pour un usage donné
    (réinitialisation mot de passe, changement d'email) et le marque comme
    utilisé s'il est valide, pour empêcher toute réutilisation. Retourne
    l'OTPCode si valide, None sinon (code inconnu, déjà utilisé ou expiré).
    """
    otp = OTPCode.objects.using('default').filter(
        user=user, purpose=purpose, code=code, is_used=False
    ).order_by('-created_at').first()
    if not otp or not otp.is_valid():
        return None
    otp.is_used = True
    otp.save(using='default', update_fields=['is_used'])
    return otp


# Dispatch order_type -> (db alias, modèle, champs client_id/livreur_id/coursier_id).
# Résolu paresseusement (imports locaux) pour éviter tout import circulaire
# authentication <-> delivery/market/marketplace au chargement du module.
def _order_dispatch():
    from apps.delivery.models import DeliveryOrder
    from apps.market.models import MarketRequest
    from apps.marketplace.models import MarketplaceOrder
    return {
        'DELIVERY': ('delivery_db', DeliveryOrder, 'livreur_id'),
        'MARKET': ('market_db', MarketRequest, None),  # géré séparément (coursier ou livreur selon le statut)
        'MARKETPLACE': ('marketplace_db', MarketplaceOrder, 'livreur_id'),
    }


def validate_order_reference(order_type, order_id):
    """
    Vérifie qu'une commande référencée par (order_type, order_id) existe
    réellement dans sa base de service. Nécessaire pour tout write path qui
    accepte order_type/order_id bruts depuis l'utilisateur (ex: mise à jour
    de position livreur) : sans jointure ORM cross-db possible, rien d'autre
    n'empêche d'enregistrer une référence orpheline. Lève ValidationError si
    le type ou l'id est invalide.
    """
    dispatch = _order_dispatch()
    if order_type not in dispatch:
        raise serializers.ValidationError({'order_type': 'Type de commande invalide.'})
    db_alias, model, _ = dispatch[order_type]
    if not model.objects.using(db_alias).filter(id=order_id).exists():
        raise serializers.ValidationError({'order_id': "Cette commande n'existe pas."})


def get_order_participants(order_type, order_id):
    """
    Résout (client_id, assignee_id) pour une commande, quel que soit le
    service qui la possède. Une seule requête `.values().get()` (pas de
    jointure ORM cross-db, donc autorisée par le routeur) ; le résultat est
    figé sur la Conversation à sa création, pas re-résolu à chaque message.
    Retourne None si la commande n'a pas encore d'assigné (ex: MarketRequest
    encore OPEN) ou si elle est introuvable.
    """
    dispatch = _order_dispatch()
    if order_type not in dispatch:
        return None
    db_alias, model, assignee_field = dispatch[order_type]

    if order_type == 'MARKET':
        try:
            row = model.objects.using(db_alias).values(
                'client_id', 'coursier_id', 'livreur_id', 'status'
            ).get(id=order_id)
        except model.DoesNotExist:
            return None
        # Pendant les courses : le coursier est l'assigné. Une fois la
        # livraison finale entamée, le livreur prend le relais (voir
        # unique_together sur Conversation qui autorise les deux en parallèle).
        assignee_id = row['livreur_id'] if row['status'] in ('DELIVERING', 'COMPLETED') else row['coursier_id']
        if not assignee_id:
            return None
        return {'client_id': row['client_id'], 'assignee_id': assignee_id}

    try:
        row = model.objects.using(db_alias).values('client_id', assignee_field).get(id=order_id)
    except model.DoesNotExist:
        return None
    assignee_id = row[assignee_field]
    if not assignee_id:
        return None
    return {'client_id': row['client_id'], 'assignee_id': assignee_id}


def open_conversation(order_type, order_id, requesting_user_id):
    """
    Ouvre (ou récupère) la conversation entre le client et l'assigné courant
    d'une commande. Vérifie que l'utilisateur demandeur est bien l'un des
    deux participants avant de créer quoi que ce soit.
    """
    from rest_framework.exceptions import ValidationError, PermissionDenied

    participants = get_order_participants(order_type, order_id)
    if not participants:
        raise ValidationError({'order_id': "Cette commande n'a pas encore d'acteur assigné."})

    if requesting_user_id not in (participants['client_id'], participants['assignee_id']):
        raise PermissionDenied("Vous ne faites pas partie de cette commande.")

    conversation, _ = Conversation.objects.using('default').get_or_create(
        order_type=order_type, order_id=order_id, assignee_id=participants['assignee_id'],
        defaults={'client_id': participants['client_id']},
    )
    return conversation
