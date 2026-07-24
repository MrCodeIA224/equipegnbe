import pytest

from apps.marketplace.models import Shop

pytestmark = pytest.mark.django_db(databases='__all__')


def _auth(api_client, user):
    api_client.force_authenticate(user=user)


@pytest.fixture
def shop(boutiquierr_user):
    return Shop.objects.create(
        owner_id=boutiquierr_user.id, name='Boutique Test', description='...', address='Adresse',
        city='Conakry', phone='+224600000000', has_delivery=True, delivery_fee=3000,
    )


def test_shop_created_without_coordinates(shop):
    assert shop.latitude is None
    assert shop.longitude is None


def test_owner_can_set_location_via_patch(api_client, boutiquierr_user, shop):
    _auth(api_client, boutiquierr_user)
    resp = api_client.patch(f'/api/v1/marketplace/shops/{shop.id}/', {
        'latitude': '9.535000', 'longitude': '-13.679000',
    })
    assert resp.status_code == 200
    shop.refresh_from_db()
    assert str(shop.latitude) == '9.535000'
    assert str(shop.longitude) == '-13.679000'


def test_other_shop_owner_cannot_set_location(api_client, shop):
    from apps.authentication.models import User
    other_owner = User.objects.create(username='other_boutique', email='other_boutique@test.gn',
                                        role='BOUTIQUIERR', phone='+224600000098')
    other_owner.set_password('Test@1234')
    other_owner.save()

    _auth(api_client, other_owner)
    resp = api_client.patch(f'/api/v1/marketplace/shops/{shop.id}/', {
        'latitude': '9.5', 'longitude': '-13.6',
    })
    assert resp.status_code == 403


def test_shop_list_exposes_coordinates(api_client, shop):
    shop.latitude = '9.535000'
    shop.longitude = '-13.679000'
    shop.save()

    resp = api_client.get('/api/v1/marketplace/shops/')
    assert resp.status_code == 200
    result = next(r for r in resp.data['results'] if r['id'] == shop.id)
    assert result['latitude'] == '9.535000'
