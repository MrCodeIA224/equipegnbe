import pytest

pytestmark = pytest.mark.django_db


def _auth(api_client, user):
    api_client.force_authenticate(user=user)


def test_create_and_list_address(api_client, client_user):
    _auth(api_client, client_user)
    resp = api_client.post('/api/v1/auth/addresses/', {
        'label': 'Maison', 'full_address': 'Quartier Almamya', 'city': 'Conakry', 'is_default': True,
    })
    assert resp.status_code == 201

    resp = api_client.get('/api/v1/auth/addresses/')
    assert resp.data['count'] == 1


def test_setting_new_default_unsets_previous_default(api_client, client_user):
    _auth(api_client, client_user)
    api_client.post('/api/v1/auth/addresses/', {
        'label': 'Maison', 'full_address': 'Adresse 1', 'city': 'Conakry', 'is_default': True,
    })
    api_client.post('/api/v1/auth/addresses/', {
        'label': 'Bureau', 'full_address': 'Adresse 2', 'city': 'Conakry', 'is_default': True,
    })

    from apps.authentication.models import Address
    defaults = Address.objects.filter(user=client_user, is_default=True)
    assert defaults.count() == 1
    assert defaults.first().label == 'Bureau'


def test_user_cannot_see_another_users_addresses(api_client, client_user, restaurant_user):
    from apps.authentication.models import Address
    Address.objects.create(user=restaurant_user, label='Autre', full_address='X', city='Conakry')

    _auth(api_client, client_user)
    resp = api_client.get('/api/v1/auth/addresses/')
    assert resp.data['count'] == 0


def test_invalid_city_choice_rejected(api_client, client_user):
    _auth(api_client, client_user)
    resp = api_client.post('/api/v1/auth/addresses/', {
        'label': 'Test', 'full_address': 'X', 'city': 'VilleInexistante',
    })
    assert resp.status_code == 400


def test_address_coordinates_round_trip(api_client, client_user):
    _auth(api_client, client_user)
    resp = api_client.post('/api/v1/auth/addresses/', {
        'label': 'Maison', 'full_address': 'Quartier Almamya', 'city': 'Conakry',
        'latitude': '9.535000', 'longitude': '-13.679000',
    })
    assert resp.status_code == 201
    assert resp.data['latitude'] == '9.535000'
    assert resp.data['longitude'] == '-13.679000'


def test_address_coordinates_are_optional(api_client, client_user):
    _auth(api_client, client_user)
    resp = api_client.post('/api/v1/auth/addresses/', {
        'label': 'Maison', 'full_address': 'Quartier Almamya', 'city': 'Conakry',
    })
    assert resp.status_code == 201
    assert resp.data['latitude'] is None
    assert resp.data['longitude'] is None
