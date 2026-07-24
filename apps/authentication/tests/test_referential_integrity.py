import pytest
from io import StringIO
from django.core.management import call_command
from rest_framework.exceptions import ValidationError

from apps.authentication.services import validate_order_reference
from apps.authentication.models import Notification, Conversation, LivreurPosition
from apps.delivery.models import Restaurant, MenuItem, DeliveryOrder, DeliveryPayment

pytestmark = pytest.mark.django_db(databases='__all__')


def _auth(api_client, user):
    api_client.force_authenticate(user=user)


def _make_delivery_order(client_user):
    restaurant = Restaurant.objects.create(
        owner_id=999999, name='Chez Test', description='...', address='Adresse',
        city='Conakry', phone='+224600000000', delivery_fee=5000,
    )
    menu_item = MenuItem.objects.create(restaurant=restaurant, name='Plat', price=10000)
    order = DeliveryOrder.objects.create(
        client_id=client_user.id, restaurant=restaurant,
        delivery_address='Adresse', delivery_city='Conakry',
        items_total=menu_item.price, delivery_fee=restaurant.delivery_fee,
        total_price=menu_item.price + restaurant.delivery_fee,
    )
    DeliveryPayment.objects.create(order=order, method=DeliveryPayment.Method.CASH_ON_DELIVERY,
                                    status=DeliveryPayment.Status.CONFIRMED)
    return order


def test_validate_order_reference_accepts_existing_order(client_user):
    order = _make_delivery_order(client_user)
    validate_order_reference('DELIVERY', order.id)  # ne doit pas lever


def test_validate_order_reference_rejects_unknown_order_type():
    with pytest.raises(ValidationError):
        validate_order_reference('BOGUS', 1)


def test_validate_order_reference_rejects_nonexistent_order_id(client_user):
    with pytest.raises(ValidationError):
        validate_order_reference('DELIVERY', 999999)


def test_livreur_position_rejects_nonexistent_order(api_client, livreur_user):
    _auth(api_client, livreur_user)
    resp = api_client.post('/api/v1/auth/livreurs/position/', {
        'latitude': '9.1', 'longitude': '-13.1', 'order_type': 'DELIVERY', 'order_id': 999999,
    })
    assert resp.status_code == 400


def test_livreur_position_accepts_existing_order(api_client, livreur_user, client_user):
    order = _make_delivery_order(client_user)
    _auth(api_client, livreur_user)
    resp = api_client.post('/api/v1/auth/livreurs/position/', {
        'latitude': '9.1', 'longitude': '-13.1', 'order_type': 'DELIVERY', 'order_id': order.id,
    })
    assert resp.status_code == 200
    position = LivreurPosition.objects.get(livreur=livreur_user)
    assert position.current_order_type == 'DELIVERY'
    assert position.current_order_id == order.id


def test_livreur_position_rejects_order_type_without_order_id(api_client, livreur_user):
    _auth(api_client, livreur_user)
    resp = api_client.post('/api/v1/auth/livreurs/position/', {
        'latitude': '9.1', 'longitude': '-13.1', 'order_type': 'DELIVERY',
    })
    assert resp.status_code == 400


def test_check_referential_integrity_reports_clean_state(client_user):
    order = _make_delivery_order(client_user)
    Notification.objects.create(
        recipient=client_user, title='Test', message='Test',
        order_type='DELIVERY', order_id=order.id,
    )

    out = StringIO()
    call_command('check_referential_integrity', stdout=out)
    assert 'Aucune référence orpheline' in out.getvalue()


def test_check_referential_integrity_detects_orphan(client_user):
    Notification.objects.create(
        recipient=client_user, title='Test', message='Test',
        order_type='DELIVERY', order_id=999999,
    )

    out = StringIO()
    call_command('check_referential_integrity', stdout=out)
    output = out.getvalue()
    assert 'orpheline' in output
    assert 'DELIVERY#999999' in output


def test_check_referential_integrity_detects_orphan_conversation(client_user, livreur_user):
    Conversation.objects.create(
        order_type='DELIVERY', order_id=999999,
        client=client_user, assignee=livreur_user,
    )

    out = StringIO()
    call_command('check_referential_integrity', stdout=out)
    assert 'Conversation' in out.getvalue()
