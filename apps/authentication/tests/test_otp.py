import pytest
from django.utils import timezone
from datetime import timedelta

from apps.authentication.models import OTPCode

pytestmark = pytest.mark.django_db


def _auth(api_client, user):
    api_client.force_authenticate(user=user)


# ---------------------------------------------------------------------------
# Mot de passe oublié
# ---------------------------------------------------------------------------

def test_password_reset_request_returns_otp_for_known_email(api_client, client_user):
    resp = api_client.post('/api/v1/auth/password-reset/request/', {'email': 'client1@test.gn'})
    assert resp.status_code == 200
    assert 'simulated_otp' in resp.data
    assert OTPCode.objects.filter(user=client_user, purpose=OTPCode.Purpose.PASSWORD_RESET).exists()


def test_password_reset_request_rejects_unknown_email(api_client):
    resp = api_client.post('/api/v1/auth/password-reset/request/', {'email': 'nobody@test.gn'})
    assert resp.status_code == 404


def test_password_reset_confirm_changes_password(api_client, client_user):
    resp = api_client.post('/api/v1/auth/password-reset/request/', {'email': 'client1@test.gn'})
    otp_code = resp.data['simulated_otp']

    resp = api_client.post('/api/v1/auth/password-reset/confirm/', {
        'email': 'client1@test.gn', 'otp_code': otp_code,
        'new_password': 'NewPass@2024', 'new_password2': 'NewPass@2024',
    })
    assert resp.status_code == 200

    resp = api_client.post('/api/v1/auth/login/', {'username': 'client1', 'password': 'NewPass@2024'})
    assert resp.status_code == 200


def test_password_reset_confirm_rejects_wrong_otp(api_client, client_user):
    api_client.post('/api/v1/auth/password-reset/request/', {'email': 'client1@test.gn'})
    resp = api_client.post('/api/v1/auth/password-reset/confirm/', {
        'email': 'client1@test.gn', 'otp_code': '0000',
        'new_password': 'NewPass@2024', 'new_password2': 'NewPass@2024',
    })
    assert resp.status_code == 400


def test_password_reset_confirm_rejects_expired_otp(api_client, client_user):
    otp = OTPCode.objects.create(
        user=client_user, purpose=OTPCode.Purpose.PASSWORD_RESET, code='1234',
        expires_at=timezone.now() - timedelta(minutes=1),
    )
    resp = api_client.post('/api/v1/auth/password-reset/confirm/', {
        'email': 'client1@test.gn', 'otp_code': otp.code,
        'new_password': 'NewPass@2024', 'new_password2': 'NewPass@2024',
    })
    assert resp.status_code == 400


def test_password_reset_confirm_rejects_mismatched_passwords(api_client, client_user):
    resp = api_client.post('/api/v1/auth/password-reset/request/', {'email': 'client1@test.gn'})
    otp_code = resp.data['simulated_otp']

    resp = api_client.post('/api/v1/auth/password-reset/confirm/', {
        'email': 'client1@test.gn', 'otp_code': otp_code,
        'new_password': 'NewPass@2024', 'new_password2': 'Different@2024',
    })
    assert resp.status_code == 400


def test_password_reset_otp_cannot_be_reused(api_client, client_user):
    resp = api_client.post('/api/v1/auth/password-reset/request/', {'email': 'client1@test.gn'})
    otp_code = resp.data['simulated_otp']

    api_client.post('/api/v1/auth/password-reset/confirm/', {
        'email': 'client1@test.gn', 'otp_code': otp_code,
        'new_password': 'NewPass@2024', 'new_password2': 'NewPass@2024',
    })
    resp = api_client.post('/api/v1/auth/password-reset/confirm/', {
        'email': 'client1@test.gn', 'otp_code': otp_code,
        'new_password': 'AnotherPass@2024', 'new_password2': 'AnotherPass@2024',
    })
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Changement d'email (utilisateur connecté)
# ---------------------------------------------------------------------------

def test_email_change_request_requires_authentication(api_client):
    resp = api_client.post('/api/v1/auth/me/email-change/request/', {
        'current_email': 'client1@test.gn', 'new_email': 'new@test.gn',
    })
    assert resp.status_code in (401, 403)


def test_email_change_request_rejects_wrong_current_email(api_client, client_user):
    _auth(api_client, client_user)
    resp = api_client.post('/api/v1/auth/me/email-change/request/', {
        'current_email': 'wrong@test.gn', 'new_email': 'new@test.gn',
    })
    assert resp.status_code == 400


def test_email_change_request_rejects_email_already_used(api_client, client_user, restaurant_user):
    _auth(api_client, client_user)
    resp = api_client.post('/api/v1/auth/me/email-change/request/', {
        'current_email': client_user.email, 'new_email': restaurant_user.email,
    })
    assert resp.status_code == 400


def test_email_change_request_does_not_change_email_yet(api_client, client_user):
    _auth(api_client, client_user)
    original_email = client_user.email
    api_client.post('/api/v1/auth/me/email-change/request/', {
        'current_email': client_user.email, 'new_email': 'new@test.gn',
    })
    client_user.refresh_from_db()
    assert client_user.email == original_email


def test_email_change_confirm_applies_new_email(api_client, client_user):
    _auth(api_client, client_user)
    resp = api_client.post('/api/v1/auth/me/email-change/request/', {
        'current_email': client_user.email, 'new_email': 'new@test.gn',
    })
    otp_code = resp.data['simulated_otp']

    resp = api_client.post('/api/v1/auth/me/email-change/confirm/', {'otp_code': otp_code})
    assert resp.status_code == 200
    assert resp.data['email'] == 'new@test.gn'
    client_user.refresh_from_db()
    assert client_user.email == 'new@test.gn'


def test_email_change_confirm_rejects_wrong_otp(api_client, client_user):
    _auth(api_client, client_user)
    api_client.post('/api/v1/auth/me/email-change/request/', {
        'current_email': client_user.email, 'new_email': 'new@test.gn',
    })
    resp = api_client.post('/api/v1/auth/me/email-change/confirm/', {'otp_code': '0000'})
    assert resp.status_code == 400
    client_user.refresh_from_db()
    assert client_user.email != 'new@test.gn'
