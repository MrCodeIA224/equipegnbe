"""URLs principales GnExpress"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

admin.site.site_header = "GnExpress - Administration"
admin.site.site_title = "GnExpress Admin"
admin.site.index_title = "Tableau de bord d'administration"

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/auth/', include('apps.authentication.urls')),
    path('api/v1/delivery/', include('apps.delivery.urls')),
    path('api/v1/market/', include('apps.market.urls')),
    path('api/v1/marketplace/', include('apps.marketplace.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
