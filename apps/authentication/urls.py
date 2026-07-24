from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    LoginView, RegisterView, MeView, ChangePasswordView,
    LogoutView, LivreurListView, AdminUserViewSet,
    AddressViewSet, PromoCodeValidateView, PromoCodeViewSet, PromoRedemptionViewSet,
)

router = DefaultRouter()
router.register(r'admin/users', AdminUserViewSet, basename='admin-users')
router.register(r'addresses', AddressViewSet, basename='address')
router.register(r'admin/promo-codes', PromoCodeViewSet, basename='admin-promo-codes')
router.register(r'admin/promo-redemptions', PromoRedemptionViewSet, basename='admin-promo-redemptions')

urlpatterns = [
    # Auth
    path('login/', LoginView.as_view(), name='login'),
    path('register/', RegisterView.as_view(), name='register'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token-refresh'),
    path('logout/', LogoutView.as_view(), name='logout'),

    # Profil
    path('me/', MeView.as_view(), name='me'),
    path('me/change-password/', ChangePasswordView.as_view(), name='change-password'),

    # Ressource partagée inter-services
    path('livreurs/available/', LivreurListView.as_view(), name='livreurs-available'),

    # Codes promo (checkout, cross-service)
    path('promo-codes/validate/', PromoCodeValidateView.as_view(), name='promo-code-validate'),

    # Admin
    path('', include(router.urls)),
]
