import pytest
from rest_framework.exceptions import ValidationError, PermissionDenied

from apps.authentication.services import open_conversation, get_order_participants
from apps.authentication.models import Conversation
from apps.delivery.models import Restaurant, MenuItem, DeliveryOrder, DeliveryPayment
from apps.market.models import MarketRequest

pytestmark = pytest.mark.django_db(databases='__all__')


def _auth(api_client, user):
    api_client.force_authenticate(user=user)


def _make_delivery_order(client_user, livreur_user=None):
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
    if livreur_user:
        order.livreur_id = livreur_user.id
        order.save()
    return order


def test_get_order_participants_returns_none_without_assignee(client_user):
    order = _make_delivery_order(client_user)
    assert get_order_participants('DELIVERY', order.id) is None


def test_get_order_participants_resolves_delivery_assignee(client_user, livreur_user):
    order = _make_delivery_order(client_user, livreur_user)
    participants = get_order_participants('DELIVERY', order.id)
    assert participants == {'client_id': client_user.id, 'assignee_id': livreur_user.id}


def test_open_conversation_rejects_non_participant(client_user, livreur_user, restaurant_user):
    order = _make_delivery_order(client_user, livreur_user)
    with pytest.raises(PermissionDenied):
        open_conversation('DELIVERY', order.id, restaurant_user.id)


def test_open_conversation_rejects_order_without_assignee(client_user):
    order = _make_delivery_order(client_user)
    with pytest.raises(ValidationError):
        open_conversation('DELIVERY', order.id, client_user.id)


def test_open_conversation_is_idempotent(client_user, livreur_user):
    order = _make_delivery_order(client_user, livreur_user)
    conv1 = open_conversation('DELIVERY', order.id, client_user.id)
    conv2 = open_conversation('DELIVERY', order.id, livreur_user.id)
    assert conv1.id == conv2.id
    assert Conversation.objects.count() == 1


def test_market_request_gets_separate_conversations_for_coursier_and_livreur(client_user, coursier_user, livreur_user):
    req = MarketRequest.objects.create(
        client_id=client_user.id, title='Courses', market_name='Marché Madina',
        delivery_address='Adresse', delivery_city='Conakry', service_fee=10000,
        coursier_id=coursier_user.id, livreur_id=livreur_user.id, status='SHOPPING',
    )
    coursier_conv = open_conversation('MARKET', req.id, coursier_user.id)
    assert coursier_conv.assignee_id == coursier_user.id

    req.status = 'DELIVERING'
    req.save()
    livreur_conv = open_conversation('MARKET', req.id, livreur_user.id)
    assert livreur_conv.assignee_id == livreur_user.id
    assert livreur_conv.id != coursier_conv.id
    assert Conversation.objects.filter(order_type='MARKET', order_id=req.id).count() == 2


def test_conversation_open_endpoint(api_client, client_user, livreur_user):
    order = _make_delivery_order(client_user, livreur_user)
    _auth(api_client, client_user)
    resp = api_client.post('/api/v1/auth/conversations/open/', {
        'order_type': 'DELIVERY', 'order_id': order.id,
    })
    assert resp.status_code == 200
    assert resp.data['client'] == client_user.id
    assert resp.data['assignee'] == livreur_user.id


def test_send_and_list_messages(api_client, client_user, livreur_user):
    order = _make_delivery_order(client_user, livreur_user)
    conversation = open_conversation('DELIVERY', order.id, client_user.id)

    _auth(api_client, client_user)
    resp = api_client.post(f'/api/v1/auth/conversations/{conversation.id}/messages/', {'body': 'Bonjour'})
    assert resp.status_code == 201

    _auth(api_client, livreur_user)
    resp = api_client.get(f'/api/v1/auth/conversations/{conversation.id}/messages/')
    assert resp.data['count'] == 1
    assert resp.data['results'][0]['body'] == 'Bonjour'


def test_non_participant_cannot_read_messages(api_client, client_user, livreur_user, restaurant_user):
    order = _make_delivery_order(client_user, livreur_user)
    conversation = open_conversation('DELIVERY', order.id, client_user.id)

    _auth(api_client, restaurant_user)
    resp = api_client.get(f'/api/v1/auth/conversations/{conversation.id}/messages/')
    assert resp.status_code == 403
