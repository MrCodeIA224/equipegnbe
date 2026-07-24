import pytest

from apps.marketplace.models import Shop, Product, MarketplaceOrder, MarketplacePayment

pytestmark = pytest.mark.django_db(databases='__all__')


def _make_shop(owner):
    return Shop.objects.create(
        owner_id=owner.id, name='Boutique Test', description='...', address='Adresse',
        city='Conakry', phone='+224600000000', has_delivery=True, delivery_fee=3000,
    )


def _make_order(client_user, shop, product, payment_method=MarketplacePayment.Method.CASH_ON_DELIVERY):
    order = MarketplaceOrder.objects.create(
        client_id=client_user.id, shop=shop, delivery_type='DELIVERY',
        delivery_address='Adresse', delivery_city='Conakry',
        items_total=product.price, delivery_fee=shop.delivery_fee,
        total_price=product.price + shop.delivery_fee,
    )
    payment_status = (
        MarketplacePayment.Status.CONFIRMED if payment_method == MarketplacePayment.Method.CASH_ON_DELIVERY
        else MarketplacePayment.Status.PENDING
    )
    MarketplacePayment.objects.create(order=order, method=payment_method, status=payment_status)
    return order


def _auth(api_client, user):
    api_client.force_authenticate(user=user)


@pytest.fixture
def shop(boutiquierr_user):
    return _make_shop(boutiquierr_user)


@pytest.fixture
def product(shop):
    return Product.objects.create(shop=shop, name='Produit', description='...', price=15000, stock=10)


def test_full_happy_path_cash_on_delivery(api_client, client_user, boutiquierr_user, livreur_user, shop, product):
    order = _make_order(client_user, shop, product)

    _auth(api_client, boutiquierr_user)
    for new_status in ['CONFIRMED', 'PROCESSING', 'READY']:
        resp = api_client.post(f'/api/v1/marketplace/orders/{order.id}/update_status/', {'status': new_status})
        assert resp.status_code == 200, resp.data

    _auth(api_client, livreur_user)
    resp = api_client.post(f'/api/v1/marketplace/orders/{order.id}/assign_livreur/')
    assert resp.status_code == 200
    assert resp.data['status'] == 'DELIVERING'

    resp = api_client.post(f'/api/v1/marketplace/orders/{order.id}/update_status/', {'status': 'DELIVERED'})
    assert resp.status_code == 200


def test_boutiquierr_cannot_confirm_unpaid_mobile_money_order(api_client, client_user, boutiquierr_user, shop, product):
    order = _make_order(client_user, shop, product, payment_method=MarketplacePayment.Method.MTN_MOMO)
    _auth(api_client, boutiquierr_user)
    resp = api_client.post(f'/api/v1/marketplace/orders/{order.id}/update_status/', {'status': 'CONFIRMED'})
    assert resp.status_code == 400


def test_other_shop_owner_cannot_see_or_update_order(api_client, client_user, boutiquierr_user, shop, product):
    # get_queryset filtre les commandes BOUTIQUIERR sur les boutiques possédées :
    # une commande d'une autre boutique n'apparaît donc même pas (404), avant
    # d'atteindre le contrôle métier de propriété dans update_status.
    from apps.authentication.models import User
    other_owner = User.objects.create(username='other', email='other@test.gn', role='BOUTIQUIERR', phone='+224600000001')
    other_owner.set_password('Test@1234')
    other_owner.save()

    order = _make_order(client_user, shop, product)
    _auth(api_client, other_owner)
    resp = api_client.post(f'/api/v1/marketplace/orders/{order.id}/update_status/', {'status': 'CONFIRMED'})
    assert resp.status_code == 404


def test_illegal_transition_rejected(api_client, client_user, boutiquierr_user, shop, product):
    order = _make_order(client_user, shop, product)
    _auth(api_client, boutiquierr_user)
    resp = api_client.post(f'/api/v1/marketplace/orders/{order.id}/update_status/', {'status': 'DELIVERED'})
    assert resp.status_code == 400
