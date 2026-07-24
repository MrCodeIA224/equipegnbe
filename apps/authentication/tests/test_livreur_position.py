import pytest

from apps.authentication.models import LivreurPosition
from apps.authentication.services import get_livreur_position

pytestmark = pytest.mark.django_db


def _auth(api_client, user):
    api_client.force_authenticate(user=user)


def test_livreur_can_push_position(api_client, livreur_user):
    _auth(api_client, livreur_user)
    resp = api_client.post('/api/v1/auth/livreurs/position/', {
        'latitude': '9.535000', 'longitude': '-13.679000',
    })
    assert resp.status_code == 200
    position = LivreurPosition.objects.get(livreur=livreur_user)
    assert str(position.latitude) == '9.535000'
    assert str(position.longitude) == '-13.679000'


def test_pushing_again_upserts_instead_of_duplicating(api_client, livreur_user):
    _auth(api_client, livreur_user)
    api_client.post('/api/v1/auth/livreurs/position/', {'latitude': '9.1', 'longitude': '-13.1'})
    api_client.post('/api/v1/auth/livreurs/position/', {'latitude': '9.2', 'longitude': '-13.2'})

    assert LivreurPosition.objects.filter(livreur=livreur_user).count() == 1
    position = LivreurPosition.objects.get(livreur=livreur_user)
    assert str(position.latitude) == '9.200000'


def test_client_cannot_push_position(api_client, client_user):
    _auth(api_client, client_user)
    resp = api_client.post('/api/v1/auth/livreurs/position/', {'latitude': '9.1', 'longitude': '-13.1'})
    assert resp.status_code == 403


def test_missing_coordinates_rejected(api_client, livreur_user):
    _auth(api_client, livreur_user)
    resp = api_client.post('/api/v1/auth/livreurs/position/', {'latitude': '9.1'})
    assert resp.status_code == 400


def test_get_livreur_position_returns_none_when_absent(livreur_user):
    assert get_livreur_position(livreur_user.id) is None


def test_get_livreur_position_returns_last_known_position(livreur_user):
    LivreurPosition.objects.create(livreur=livreur_user, latitude='9.5', longitude='-13.6')
    position = get_livreur_position(livreur_user.id)
    assert position is not None
    assert str(position['latitude']) == '9.500000'
