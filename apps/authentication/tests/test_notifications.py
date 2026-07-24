import pytest

from apps.authentication.services import notify
from apps.authentication.models import Notification

pytestmark = pytest.mark.django_db


def _auth(api_client, user):
    api_client.force_authenticate(user=user)


def test_notify_creates_notification(client_user):
    notify(client_user.id, 'Titre', 'Message', notification_type='ORDER_STATUS',
           order_type='DELIVERY', order_id=42)
    notification = Notification.objects.get(recipient=client_user)
    assert notification.title == 'Titre'
    assert notification.message == 'Message'
    assert notification.order_type == 'DELIVERY'
    assert notification.order_id == 42
    assert notification.is_read is False


def test_user_only_sees_own_notifications(api_client, client_user, restaurant_user):
    notify(client_user.id, 'Pour client', 'X')
    notify(restaurant_user.id, 'Pour resto', 'Y')

    _auth(api_client, client_user)
    resp = api_client.get('/api/v1/auth/notifications/')
    assert resp.data['count'] == 1
    assert resp.data['results'][0]['title'] == 'Pour client'


def test_unread_count(api_client, client_user):
    notify(client_user.id, 'A', 'X')
    notify(client_user.id, 'B', 'Y')

    _auth(api_client, client_user)
    resp = api_client.get('/api/v1/auth/notifications/unread_count/')
    assert resp.data['unread_count'] == 2


def test_mark_read(api_client, client_user):
    notify(client_user.id, 'A', 'X')
    notification = Notification.objects.get(recipient=client_user)

    _auth(api_client, client_user)
    resp = api_client.post(f'/api/v1/auth/notifications/{notification.id}/mark_read/')
    assert resp.status_code == 200
    notification.refresh_from_db()
    assert notification.is_read is True


def test_mark_read_on_someone_elses_notification_not_found(api_client, client_user, restaurant_user):
    notify(restaurant_user.id, 'A', 'X')
    notification = Notification.objects.get(recipient=restaurant_user)

    _auth(api_client, client_user)
    resp = api_client.post(f'/api/v1/auth/notifications/{notification.id}/mark_read/')
    assert resp.status_code == 404


def test_mark_all_read(api_client, client_user):
    notify(client_user.id, 'A', 'X')
    notify(client_user.id, 'B', 'Y')

    _auth(api_client, client_user)
    resp = api_client.post('/api/v1/auth/notifications/mark_all_read/')
    assert resp.data['updated'] == 2
    assert Notification.objects.filter(recipient=client_user, is_read=False).count() == 0
