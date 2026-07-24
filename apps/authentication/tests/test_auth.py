import pytest

pytestmark = pytest.mark.django_db


def test_login_with_username(api_client, client_user):
    resp = api_client.post('/api/v1/auth/login/', {'username': 'client1', 'password': 'Test@1234'})
    assert resp.status_code == 200
    assert resp.data['user']['role'] == 'CLIENT'


def test_login_with_email(api_client, client_user):
    resp = api_client.post('/api/v1/auth/login/', {'username': 'client1@test.gn', 'password': 'Test@1234'})
    assert resp.status_code == 200
    assert resp.data['user']['username'] == 'client1'


def test_login_wrong_password_rejected(api_client, client_user):
    resp = api_client.post('/api/v1/auth/login/', {'username': 'client1', 'password': 'wrong'})
    assert resp.status_code == 401


def test_register_cannot_self_assign_admin_role(api_client):
    resp = api_client.post('/api/v1/auth/register/', {
        'username': 'wannabeadmin', 'email': 'wannabe@test.gn', 'first_name': 'A', 'last_name': 'B',
        'password': 'Test@1234', 'password2': 'Test@1234', 'role': 'ADMIN', 'phone': '+224600000000',
    })
    assert resp.status_code == 400
    assert 'role' in resp.data


def test_register_client_succeeds(api_client):
    resp = api_client.post('/api/v1/auth/register/', {
        'username': 'newclient', 'email': 'newclient@test.gn', 'first_name': 'A', 'last_name': 'B',
        'password': 'Test@1234', 'password2': 'Test@1234', 'role': 'CLIENT', 'phone': '+224600000000',
    })
    assert resp.status_code == 201
    assert 'access' in resp.data['tokens']
