import pytest

from apps.market.models import MarketRequest

pytestmark = pytest.mark.django_db(databases='__all__')


def _make_request(client_user):
    return MarketRequest.objects.create(
        client_id=client_user.id, title='Mes courses', market_name='Marché Madina',
        delivery_address='Adresse', delivery_city='Conakry', service_fee=10000,
    )


def _auth(api_client, user):
    api_client.force_authenticate(user=user)


def test_full_happy_path(api_client, client_user, coursier_user, livreur_user):
    req = _make_request(client_user)
    assert req.status == 'OPEN'

    _auth(api_client, coursier_user)
    resp = api_client.post(f'/api/v1/market/requests/{req.id}/make_offer/', {
        'message': 'Je peux faire vos courses', 'proposed_fee': 10000,
    })
    assert resp.status_code == 201
    offer_id = resp.data['id']

    _auth(api_client, client_user)
    resp = api_client.post(f'/api/v1/market/requests/{req.id}/accept_offer/', {'offer_id': offer_id})
    assert resp.status_code == 200
    assert resp.data['status'] == 'ASSIGNED'
    assert resp.data['coursier_id'] == coursier_user.id

    _auth(api_client, coursier_user)
    for new_status in ['SHOPPING', 'NEED_DELIVERY']:
        resp = api_client.post(f'/api/v1/market/requests/{req.id}/update_status/', {'status': new_status})
        assert resp.status_code == 200, resp.data

    resp = api_client.post(f'/api/v1/market/requests/{req.id}/assign_livreur/', {'livreur_id': livreur_user.id})
    assert resp.status_code == 200
    assert resp.data['livreur_id'] == livreur_user.id

    _auth(api_client, livreur_user)
    for new_status in ['DELIVERING', 'COMPLETED']:
        resp = api_client.post(f'/api/v1/market/requests/{req.id}/update_status/', {'status': new_status})
        assert resp.status_code == 200, resp.data


def test_offer_on_non_open_request_not_visible_to_unrelated_coursier(api_client, client_user, coursier_user):
    # Une fois assignée à un autre coursier, la demande sort du queryset "disponible"
    # de ce coursier (get_queryset filtre sur coursier_id=user.id OU status=OPEN) :
    # DRF renvoie donc 404 avant même d'atteindre le contrôle métier "plus disponible".
    req = _make_request(client_user)
    req.status = 'ASSIGNED'
    req.coursier_id = 999999
    req.save()

    _auth(api_client, coursier_user)
    resp = api_client.post(f'/api/v1/market/requests/{req.id}/make_offer/', {'proposed_fee': 10000})
    assert resp.status_code == 404


def test_illegal_status_transition_rejected(api_client, client_user, coursier_user):
    req = _make_request(client_user)
    _auth(api_client, coursier_user)
    resp = api_client.post(f'/api/v1/market/requests/{req.id}/update_status/', {'status': 'COMPLETED'})
    assert resp.status_code == 400


def test_client_can_cancel_open_request(api_client, client_user):
    req = _make_request(client_user)
    _auth(api_client, client_user)
    resp = api_client.post(f'/api/v1/market/requests/{req.id}/update_status/', {'status': 'CANCELLED'})
    assert resp.status_code == 200
