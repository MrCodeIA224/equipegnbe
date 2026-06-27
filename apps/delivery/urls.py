from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    RestaurantViewSet, MenuItemViewSet, FoodCategoryViewSet,
    DeliveryOrderViewSet, AdminDeliveryStatsView
)

router = DefaultRouter()
router.register(r'restaurants', RestaurantViewSet, basename='restaurant')
router.register(r'orders', DeliveryOrderViewSet, basename='delivery-order')
router.register(r'categories', FoodCategoryViewSet, basename='food-category')

urlpatterns = [
    path('', include(router.urls)),
    path('admin/stats/', AdminDeliveryStatsView.as_view(), name='delivery-admin-stats'),
    # Routes pour les articles du menu d'un restaurant
    path('restaurants/<int:restaurant_pk>/menu-items/', MenuItemViewSet.as_view({
        'get': 'list', 'post': 'create'
    }), name='restaurant-menu-items-list'),
    path('restaurants/<int:restaurant_pk>/menu-items/<int:pk>/', MenuItemViewSet.as_view({
        'get': 'retrieve', 'put': 'update', 'patch': 'partial_update', 'delete': 'destroy'
    }), name='restaurant-menu-items-detail'),
]
