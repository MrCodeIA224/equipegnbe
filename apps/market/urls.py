from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import MarketRequestViewSet, AdminMarketStatsView

router = DefaultRouter()
router.register(r'requests', MarketRequestViewSet, basename='market-request')

urlpatterns = [
    path('', include(router.urls)),
    path('admin/stats/', AdminMarketStatsView.as_view(), name='market-admin-stats'),
]
