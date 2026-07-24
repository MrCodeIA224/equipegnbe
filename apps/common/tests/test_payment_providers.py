from decimal import Decimal

from apps.common.payment_providers import OrangeMoneyProvider, MTNMoMoProvider, get_provider


def test_orange_money_initiate_returns_reference_and_otp():
    provider = OrangeMoneyProvider()
    result = provider.initiate('+224620000000', Decimal('10000'))
    assert result.transaction_reference
    assert len(result.otp_code) == 4


def test_orange_money_confirm_correct_otp_succeeds():
    provider = OrangeMoneyProvider()
    result = provider.confirm('1234', '1234')
    assert result.success is True


def test_orange_money_confirm_wrong_otp_fails():
    provider = OrangeMoneyProvider()
    result = provider.confirm('0000', '1234')
    assert result.success is False


def test_mtn_momo_provider_behaves_the_same_way():
    provider = MTNMoMoProvider()
    initiated = provider.initiate('+224622000000', Decimal('5000'))
    assert provider.confirm(initiated.otp_code, initiated.otp_code).success is True
    assert provider.confirm('9999', initiated.otp_code).success is False


def test_get_provider_registry():
    assert isinstance(get_provider('ORANGE_MONEY'), OrangeMoneyProvider)
    assert isinstance(get_provider('MTN_MOMO'), MTNMoMoProvider)


def test_get_provider_unknown_method_raises():
    import pytest
    with pytest.raises(ValueError):
        get_provider('UNKNOWN')
