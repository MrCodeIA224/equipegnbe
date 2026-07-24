import pytest

from apps.delivery.models import Restaurant, MenuItem, DeliveryOrder, DeliveryPayment
from apps.authentication.models import Notification, LivreurPosition

pytestmark = pytest.mark.django_db(databases='__all__')


def _make_restaurant(owner):
    return Restaurant.objects.create(
        owner_id=owner.id, name='Chez Test', description='...', address='Adresse',
        city='Conakry', phone='+224600000000', delivery_fee=5000,
    )


def _make_order(client_user, restaurant, menu_item):
    order = DeliveryOrder.objects.create(
        client_id=client_user.id, restaurant=restaurant,
        delivery_address='Adresse', delivery_city='Conakry',
        items_total=menu_item.price, delivery_fee=restaurant.delivery_fee,
        total_price=menu_item.price + restaurant.delivery_fee,
    )
    DeliveryPayment.objects.create(order=order, method=DeliveryPayment.Method.CASH_ON_DELIVERY,
                                    status=DeliveryPayment.Status.CONFIRMED)
    return order


def _auth(api_client, user):
    api_client.force_authenticate(user=user)


@pytest.fixture
def restaurant(restaurant_user):
    return _make_restaurant(restaurant_user)


@pytest.fixture
def menu_item(restaurant):
    return MenuItem.objects.create(restaurant=restaurant, name='Plat', price=10000)


def test_create_notifies_restaurant_owner(api_client, client_user, restaurant_user, restaurant, menu_item):
    _auth(api_client, client_user)
    resp = api_client.post('/api/v1/delivery/orders/', {
        'restaurant_id': restaurant.id, 'delivery_address': 'Adresse', 'delivery_city': 'Conakry',
        'items': [{'menu_item_id': menu_item.id, 'quantity': 1}],
        'payment_method': 'CASH_ON_DELIVERY',
    }, format='json')
    assert resp.status_code == 201, resp.data
    assert Notification.objects.filter(recipient=restaurant_user, order_type='DELIVERY').exists()


def test_confirmed_notifies_client(api_client, client_user, restaurant_user, restaurant, menu_item):
    order = _make_order(client_user, restaurant, menu_item)
    _auth(api_client, restaurant_user)
    api_client.post(f'/api/v1/delivery/orders/{order.id}/update_status/', {'status': 'CONFIRMED'})
    assert Notification.objects.filter(recipient=client_user, order_id=order.id, title='Commande confirmée').exists()


def test_delivered_notifies_client(api_client, client_user, restaurant_user, livreur_user, restaurant, menu_item):
    order = _make_order(client_user, restaurant, menu_item)
    order.status = DeliveryOrder.Status.PICKED_UP
    order.livreur_id = livreur_user.id
    order.save()

    _auth(api_client, livreur_user)
    api_client.post(f'/api/v1/delivery/orders/{order.id}/update_status/', {'status': 'DELIVERING'})
    api_client.post(f'/api/v1/delivery/orders/{order.id}/update_status/', {'status': 'DELIVERED'})
    assert Notification.objects.filter(recipient=client_user, order_id=order.id, title='Commande livrée').exists()


def test_assign_livreur_notifies_client(api_client, client_user, livreur_user, restaurant, menu_item):
    order = _make_order(client_user, restaurant, menu_item)
    order.status = DeliveryOrder.Status.READY
    order.save()

    _auth(api_client, livreur_user)
    api_client.post(f'/api/v1/delivery/orders/{order.id}/assign_livreur/')
    assert Notification.objects.filter(recipient=client_user, order_id=order.id, title='Livreur assigné').exists()


def test_cancel_delivery_notifies_restaurant_owner(api_client, client_user, restaurant_user, livreur_user, restaurant, menu_item):
    order = _make_order(client_user, restaurant, menu_item)
    order.status = DeliveryOrder.Status.PICKED_UP
    order.livreur_id = livreur_user.id
    order.save()

    _auth(api_client, livreur_user)
    api_client.post(f'/api/v1/delivery/orders/{order.id}/cancel_delivery/')
    assert Notification.objects.filter(recipient=restaurant_user, order_id=order.id).exists()


def test_livreur_position_endpoint_scoped_to_order(api_client, client_user, restaurant_user, livreur_user, restaurant, menu_item):
    order = _make_order(client_user, restaurant, menu_item)
    order.status = DeliveryOrder.Status.PICKED_UP
    order.livreur_id = livreur_user.id
    order.save()
    LivreurPosition.objects.create(livreur=livreur_user, latitude='9.5', longitude='-13.6')

    _auth(api_client, client_user)
    resp = api_client.get(f'/api/v1/delivery/orders/{order.id}/livreur-position/')
    assert resp.status_code == 200
    assert str(resp.data['latitude']) == '9.500000'


def test_livreur_position_endpoint_without_assigned_livreur(api_client, client_user, restaurant, menu_item):
    order = _make_order(client_user, restaurant, menu_item)
    _auth(api_client, client_user)
    resp = api_client.get(f'/api/v1/delivery/orders/{order.id}/livreur-position/')
    assert resp.status_code == 400
