import pytest

from apps.market.models import MarketRequest
from apps.authentication.models import Notification, LivreurPosition

pytestmark = pytest.mark.django_db(databases='__all__')


def _make_request(client_user):
    return MarketRequest.objects.create(
        client_id=client_user.id, title='Mes courses', market_name='Marché Madina',
        delivery_address='Adresse', delivery_city='Conakry', service_fee=10000,
    )


def _auth(api_client, user):
    api_client.force_authenticate(user=user)


def test_make_offer_notifies_client(api_client, client_user, coursier_user):
    req = _make_request(client_user)
    _auth(api_client, coursier_user)
    api_client.post(f'/api/v1/market/requests/{req.id}/make_offer/', {
        'message': 'Je peux faire vos courses', 'proposed_fee': 10000,
    })
    assert Notification.objects.filter(recipient=client_user, order_id=req.id, notification_type='OFFER').exists()


def test_accept_offer_notifies_coursier(api_client, client_user, coursier_user):
    req = _make_request(client_user)
    _auth(api_client, coursier_user)
    resp = api_client.post(f'/api/v1/market/requests/{req.id}/make_offer/', {'proposed_fee': 10000})
    offer_id = resp.data['id']

    _auth(api_client, client_user)
    api_client.post(f'/api/v1/market/requests/{req.id}/accept_offer/', {'offer_id': offer_id})
    assert Notification.objects.filter(recipient=coursier_user, order_id=req.id, title='Offre acceptée').exists()


def test_assign_livreur_notifies_livreur(api_client, client_user, coursier_user, livreur_user):
    req = _make_request(client_user)
    req.status = 'NEED_DELIVERY'
    req.coursier_id = coursier_user.id
    req.save()

    _auth(api_client, client_user)
    resp = api_client.post(f'/api/v1/market/requests/{req.id}/assign_livreur/', {'livreur_id': livreur_user.id})
    assert resp.status_code == 200
    assert Notification.objects.filter(
        recipient=livreur_user, order_id=req.id, title='Nouvelle mission de livraison'
    ).exists()


def test_completed_notifies_client(api_client, client_user, coursier_user, livreur_user):
    req = _make_request(client_user)
    req.status = 'DELIVERING'
    req.coursier_id = coursier_user.id
    req.livreur_id = livreur_user.id
    req.save()

    _auth(api_client, livreur_user)
    api_client.post(f'/api/v1/market/requests/{req.id}/update_status/', {'status': 'COMPLETED'})
    assert Notification.objects.filter(recipient=client_user, order_id=req.id, title='Courses terminées').exists()


def test_livreur_position_endpoint_scoped_to_request(api_client, client_user, livreur_user):
    req = _make_request(client_user)
    req.status = 'DELIVERING'
    req.livreur_id = livreur_user.id
    req.save()
    LivreurPosition.objects.create(livreur=livreur_user, latitude='9.5', longitude='-13.6')

    _auth(api_client, client_user)
    resp = api_client.get(f'/api/v1/market/requests/{req.id}/livreur-position/')
    assert resp.status_code == 200
    assert str(resp.data['latitude']) == '9.500000'


def test_livreur_position_endpoint_without_assigned_livreur(api_client, client_user):
    req = _make_request(client_user)
    _auth(api_client, client_user)
    resp = api_client.get(f'/api/v1/market/requests/{req.id}/livreur-position/')
    assert resp.status_code == 400
