import pytest
from rest_framework.test import APIClient


@pytest.fixture
def api_client():
    return APIClient()


def _make_user(db, **kwargs):
    from apps.authentication.models import User, LivreurProfile, CoursierProfile

    defaults = {
        'username': 'user', 'email': 'user@test.gn', 'phone': '+224600000000',
        'role': 'CLIENT', 'is_verified': True,
    }
    defaults.update(kwargs)
    password = defaults.pop('password', 'Test@1234')
    user = User(**defaults)
    user.set_password(password)
    user.save()
    if user.role == 'LIVREUR':
        LivreurProfile.objects.create(user=user)
    elif user.role == 'COURSIER':
        CoursierProfile.objects.create(user=user)
    return user


@pytest.fixture
def client_user(db):
    return _make_user(db, username='client1', email='client1@test.gn', role='CLIENT')


@pytest.fixture
def restaurant_user(db):
    return _make_user(db, username='resto1', email='resto1@test.gn', role='RESTAURANT')


@pytest.fixture
def livreur_user(db):
    return _make_user(db, username='livreur1', email='livreur1@test.gn', role='LIVREUR')


@pytest.fixture
def boutiquierr_user(db):
    return _make_user(db, username='boutique1', email='boutique1@test.gn', role='BOUTIQUIERR')


@pytest.fixture
def coursier_user(db):
    return _make_user(db, username='coursier1', email='coursier1@test.gn', role='COURSIER')


@pytest.fixture
def admin_user(db):
    return _make_user(db, username='admin1', email='admin1@test.gn', role='ADMIN', is_staff=True, is_superuser=True)
