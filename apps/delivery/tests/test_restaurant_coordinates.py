import pytest

from apps.delivery.models import Restaurant

pytestmark = pytest.mark.django_db(databases='__all__')


def _auth(api_client, user):
    api_client.force_authenticate(user=user)


@pytest.fixture
def restaurant(restaurant_user):
    return Restaurant.objects.create(
        owner_id=restaurant_user.id, name='Chez Test', description='...', address='Adresse',
        city='Conakry', phone='+224600000000', delivery_fee=5000,
    )


def test_restaurant_created_without_coordinates(restaurant):
    assert restaurant.latitude is None
    assert restaurant.longitude is None


def test_owner_can_set_location_via_patch(api_client, restaurant_user, restaurant):
    _auth(api_client, restaurant_user)
    resp = api_client.patch(f'/api/v1/delivery/restaurants/{restaurant.id}/', {
        'latitude': '9.535000', 'longitude': '-13.679000',
    })
    assert resp.status_code == 200
    restaurant.refresh_from_db()
    assert str(restaurant.latitude) == '9.535000'
    assert str(restaurant.longitude) == '-13.679000'


def test_other_restaurant_owner_cannot_set_location(api_client, restaurant):
    from apps.authentication.models import User
    other_owner = User.objects.create(username='other_resto', email='other_resto@test.gn',
                                        role='RESTAURANT', phone='+224600000099')
    other_owner.set_password('Test@1234')
    other_owner.save()

    _auth(api_client, other_owner)
    resp = api_client.patch(f'/api/v1/delivery/restaurants/{restaurant.id}/', {
        'latitude': '9.5', 'longitude': '-13.6',
    })
    assert resp.status_code == 403


def test_restaurant_list_exposes_coordinates(api_client, restaurant):
    restaurant.latitude = '9.535000'
    restaurant.longitude = '-13.679000'
    restaurant.save()

    resp = api_client.get('/api/v1/delivery/restaurants/')
    assert resp.status_code == 200
    result = next(r for r in resp.data['results'] if r['id'] == restaurant.id)
    assert result['latitude'] == '9.535000'
