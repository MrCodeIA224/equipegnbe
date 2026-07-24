import pytest

from apps.delivery.models import Restaurant, MenuItem, DeliveryOrder, DeliveryPayment

pytestmark = pytest.mark.django_db(databases='__all__')


def _make_restaurant(owner):
    return Restaurant.objects.create(
        owner_id=owner.id, name='Chez Test', description='...', address='Adresse',
        city='Conakry', phone='+224600000000', delivery_fee=5000,
    )


def _make_order(client_user, restaurant, menu_item, payment_method=DeliveryPayment.Method.CASH_ON_DELIVERY):
    order = DeliveryOrder.objects.create(
        client_id=client_user.id, restaurant=restaurant,
        delivery_address='Adresse', delivery_city='Conakry',
        items_total=menu_item.price, delivery_fee=restaurant.delivery_fee,
        total_price=menu_item.price + restaurant.delivery_fee,
    )
    payment_status = (
        DeliveryPayment.Status.CONFIRMED if payment_method == DeliveryPayment.Method.CASH_ON_DELIVERY
        else DeliveryPayment.Status.PENDING
    )
    DeliveryPayment.objects.create(order=order, method=payment_method, status=payment_status)
    return order


def _auth(api_client, user):
    api_client.force_authenticate(user=user)


@pytest.fixture
def restaurant(restaurant_user):
    return _make_restaurant(restaurant_user)


@pytest.fixture
def menu_item(restaurant):
    return MenuItem.objects.create(restaurant=restaurant, name='Plat', price=10000)


def test_full_happy_path_cash_on_delivery(api_client, client_user, restaurant_user, livreur_user, restaurant, menu_item):
    order = _make_order(client_user, restaurant, menu_item)

    _auth(api_client, restaurant_user)
    for new_status in ['CONFIRMED', 'PREPARING', 'READY']:
        resp = api_client.post(f'/api/v1/delivery/orders/{order.id}/update_status/', {'status': new_status})
        assert resp.status_code == 200, resp.data

    _auth(api_client, livreur_user)
    resp = api_client.post(f'/api/v1/delivery/orders/{order.id}/assign_livreur/')
    assert resp.status_code == 200
    assert resp.data['status'] == 'PICKED_UP'

    for new_status in ['DELIVERING', 'DELIVERED']:
        resp = api_client.post(f'/api/v1/delivery/orders/{order.id}/update_status/', {'status': new_status})
        assert resp.status_code == 200, resp.data


def test_client_cannot_skip_to_preparing(api_client, client_user, restaurant_user, restaurant, menu_item):
    order = _make_order(client_user, restaurant, menu_item)
    _auth(api_client, client_user)
    resp = api_client.post(f'/api/v1/delivery/orders/{order.id}/update_status/', {'status': 'PREPARING'})
    assert resp.status_code == 400


def test_restaurant_cannot_confirm_unpaid_mobile_money_order(api_client, client_user, restaurant_user, restaurant, menu_item):
    order = _make_order(client_user, restaurant, menu_item, payment_method=DeliveryPayment.Method.ORANGE_MONEY)
    _auth(api_client, restaurant_user)
    resp = api_client.post(f'/api/v1/delivery/orders/{order.id}/update_status/', {'status': 'CONFIRMED'})
    assert resp.status_code == 400
    assert 'Paiement' in resp.data['error']


def test_restaurant_can_confirm_once_mobile_money_payment_confirmed(api_client, client_user, restaurant_user, restaurant, menu_item):
    order = _make_order(client_user, restaurant, menu_item, payment_method=DeliveryPayment.Method.ORANGE_MONEY)
    order.payment.status = DeliveryPayment.Status.CONFIRMED
    order.payment.save()

    _auth(api_client, restaurant_user)
    resp = api_client.post(f'/api/v1/delivery/orders/{order.id}/update_status/', {'status': 'CONFIRMED'})
    assert resp.status_code == 200


def test_livreur_cancel_requires_restaurant_confirmation_to_reopen(api_client, client_user, restaurant_user, livreur_user, restaurant, menu_item):
    order = _make_order(client_user, restaurant, menu_item)
    order.status = DeliveryOrder.Status.READY
    order.save()

    _auth(api_client, livreur_user)
    api_client.post(f'/api/v1/delivery/orders/{order.id}/assign_livreur/')

    resp = api_client.post(f'/api/v1/delivery/orders/{order.id}/cancel_delivery/')
    assert resp.status_code == 200
    assert resp.data['status'] == 'LIVREUR_CANCELLED'

    _auth(api_client, restaurant_user)
    resp = api_client.post(f'/api/v1/delivery/orders/{order.id}/update_status/', {'status': 'READY'})
    assert resp.status_code == 200
    order.refresh_from_db()
    assert order.livreur_id is None
