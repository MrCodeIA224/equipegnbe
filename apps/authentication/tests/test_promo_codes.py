from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.authentication.models import PromoCode, PromoRedemption
from apps.authentication.services import validate_and_apply_promo, redeem_promo

pytestmark = pytest.mark.django_db


def _make_promo(**kwargs):
    defaults = {
        'code': 'TEST10', 'discount_type': PromoCode.DiscountType.PERCENTAGE,
        'value': Decimal('10'), 'min_order_amount': Decimal('0'),
        'applicable_order_types': [], 'is_active': True,
    }
    defaults.update(kwargs)
    return PromoCode.objects.create(**defaults)


def test_valid_percentage_promo_applies_discount(client_user):
    _make_promo()
    result = validate_and_apply_promo('TEST10', client_user, 'DELIVERY', Decimal('20000'))
    assert result['discount_amount'] == Decimal('2000')


def test_valid_fixed_promo_applies_discount(client_user):
    _make_promo(code='FIXE5000', discount_type=PromoCode.DiscountType.FIXED, value=Decimal('5000'))
    result = validate_and_apply_promo('FIXE5000', client_user, 'DELIVERY', Decimal('20000'))
    assert result['discount_amount'] == Decimal('5000')


def test_fixed_discount_capped_at_subtotal(client_user):
    _make_promo(code='FIXE5000', discount_type=PromoCode.DiscountType.FIXED, value=Decimal('50000'))
    result = validate_and_apply_promo('FIXE5000', client_user, 'DELIVERY', Decimal('3000'))
    assert result['discount_amount'] == Decimal('3000')


def test_expired_promo_rejected(client_user):
    _make_promo(expiry_date=timezone.now() - timedelta(days=1))
    with pytest.raises(ValidationError):
        validate_and_apply_promo('TEST10', client_user, 'DELIVERY', Decimal('20000'))


def test_usage_limit_reached_rejected(client_user):
    _make_promo(usage_limit=1, times_used=1)
    with pytest.raises(ValidationError):
        validate_and_apply_promo('TEST10', client_user, 'DELIVERY', Decimal('20000'))


def test_min_order_amount_not_met_rejected(client_user):
    _make_promo(min_order_amount=Decimal('50000'))
    with pytest.raises(ValidationError):
        validate_and_apply_promo('TEST10', client_user, 'DELIVERY', Decimal('20000'))


def test_wrong_order_type_rejected(client_user):
    _make_promo(applicable_order_types=['MARKETPLACE'])
    with pytest.raises(ValidationError):
        validate_and_apply_promo('TEST10', client_user, 'DELIVERY', Decimal('20000'))


def test_inactive_promo_rejected(client_user):
    _make_promo(is_active=False)
    with pytest.raises(ValidationError):
        validate_and_apply_promo('TEST10', client_user, 'DELIVERY', Decimal('20000'))


def test_same_user_cannot_redeem_twice(client_user):
    promo = _make_promo()
    redeem_promo(promo, client_user, 'DELIVERY', order_id=1, discount_amount=Decimal('2000'))

    with pytest.raises(ValidationError):
        validate_and_apply_promo('TEST10', client_user, 'DELIVERY', Decimal('20000'))


def test_redeem_promo_increments_times_used(client_user):
    promo = _make_promo()
    redeem_promo(promo, client_user, 'DELIVERY', order_id=1, discount_amount=Decimal('2000'))
    promo.refresh_from_db()
    assert promo.times_used == 1
    assert PromoRedemption.objects.filter(promo_code=promo, user=client_user).count() == 1
