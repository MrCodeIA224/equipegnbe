from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    CategoryViewSet, ShopViewSet, ProductViewSet,
    MarketplaceOrderViewSet, AdminMarketplaceStatsView
)

router = DefaultRouter()
router.register(r'categories', CategoryViewSet, basename='category')
router.register(r'shops', ShopViewSet, basename='shop')
router.register(r'products', ProductViewSet, basename='product')
router.register(r'orders', MarketplaceOrderViewSet, basename='marketplace-order')

urlpatterns = [
    path('', include(router.urls)),
    path('admin/stats/', AdminMarketplaceStatsView.as_view(), name='marketplace-admin-stats'),
]
