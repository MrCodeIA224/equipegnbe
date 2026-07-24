import pytest

from apps.marketplace.models import Shop, Product, MarketplaceOrder, MarketplacePayment
from apps.authentication.models import Notification

pytestmark = pytest.mark.django_db(databases='__all__')


def _make_shop(owner):
    return Shop.objects.create(
        owner_id=owner.id, name='Boutique Test', description='...', address='Adresse',
        city='Conakry', phone='+224600000000', has_delivery=True, delivery_fee=3000,
    )


def _make_order(client_user, shop, product):
    order = MarketplaceOrder.objects.create(
        client_id=client_user.id, shop=shop, delivery_type='DELIVERY',
        delivery_address='Adresse', delivery_city='Conakry',
        items_total=product.price, delivery_fee=shop.delivery_fee,
        total_price=product.price + shop.delivery_fee,
    )
    MarketplacePayment.objects.create(order=order, method=MarketplacePayment.Method.CASH_ON_DELIVERY,
                                       status=MarketplacePayment.Status.CONFIRMED)
    return order


def _auth(api_client, user):
    api_client.force_authenticate(user=user)


@pytest.fixture
def shop(boutiquierr_user):
    return _make_shop(boutiquierr_user)


@pytest.fixture
def product(shop):
    return Product.objects.create(shop=shop, name='Produit', description='...', price=15000, stock=10)


def test_create_notifies_shop_owner(api_client, client_user, boutiquierr_user, shop, product):
    _auth(api_client, client_user)
    resp = api_client.post('/api/v1/marketplace/orders/', {
        'shop_id': shop.id, 'delivery_type': 'DELIVERY',
        'delivery_address': 'Adresse', 'delivery_city': 'Conakry',
        'items': [{'product_id': product.id, 'quantity': 1}],
        'payment_method': 'CASH_ON_DELIVERY',
    }, format='json')
    assert resp.status_code == 201, resp.data
    assert Notification.objects.filter(recipient=boutiquierr_user, order_type='MARKETPLACE').exists()


def test_confirmed_notifies_client(api_client, client_user, boutiquierr_user, shop, product):
    order = _make_order(client_user, shop, product)
    _auth(api_client, boutiquierr_user)
    api_client.post(f'/api/v1/marketplace/orders/{order.id}/update_status/', {'status': 'CONFIRMED'})
    assert Notification.objects.filter(recipient=client_user, order_id=order.id, title='Commande confirmée').exists()


def test_delivered_notifies_client(api_client, client_user, boutiquierr_user, livreur_user, shop, product):
    order = _make_order(client_user, shop, product)
    order.status = MarketplaceOrder.Status.DELIVERING
    order.livreur_id = livreur_user.id
    order.save()

    _auth(api_client, livreur_user)
    api_client.post(f'/api/v1/marketplace/orders/{order.id}/update_status/', {'status': 'DELIVERED'})
    assert Notification.objects.filter(recipient=client_user, order_id=order.id, title='Commande livrée').exists()


def test_assign_livreur_self_assign_notifies_client(api_client, client_user, livreur_user, shop, product):
    order = _make_order(client_user, shop, product)
    order.status = MarketplaceOrder.Status.READY
    order.save()

    _auth(api_client, livreur_user)
    api_client.post(f'/api/v1/marketplace/orders/{order.id}/assign_livreur/')
    assert Notification.objects.filter(recipient=client_user, order_id=order.id, title='Livreur assigné').exists()


def test_assign_livreur_by_admin_notifies_client(api_client, client_user, admin_user, livreur_user, shop, product):
    order = _make_order(client_user, shop, product)
    order.status = MarketplaceOrder.Status.READY
    order.save()

    _auth(api_client, admin_user)
    api_client.post(f'/api/v1/marketplace/orders/{order.id}/assign_livreur/', {'livreur_id': livreur_user.id})
    assert Notification.objects.filter(recipient=client_user, order_id=order.id, title='Livreur assigné').exists()


def test_cancel_delivery_notifies_shop_owner(api_client, client_user, boutiquierr_user, livreur_user, shop, product):
    order = _make_order(client_user, shop, product)
    order.status = MarketplaceOrder.Status.DELIVERING
    order.livreur_id = livreur_user.id
    order.save()

    _auth(api_client, livreur_user)
    api_client.post(f'/api/v1/marketplace/orders/{order.id}/cancel_delivery/')
    assert Notification.objects.filter(recipient=boutiquierr_user, order_id=order.id).exists()
