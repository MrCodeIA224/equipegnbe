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

from .models import PromoCode, PromoRedemption


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
