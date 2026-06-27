from django.contrib import admin
from .models import MarketRequest, MarketItem, CoursierOffer, MarketRating


class MarketItemInline(admin.TabularInline):
    model = MarketItem
    extra = 0


class CoursierOfferInline(admin.TabularInline):
    model = CoursierOffer
    extra = 0
    readonly_fields = ['coursier_id', 'proposed_fee', 'message', 'is_accepted', 'created_at']


@admin.register(MarketRequest)
class MarketRequestAdmin(admin.ModelAdmin):
    list_display = ['id', 'title', 'market_name', 'client_id', 'status', 'budget', 'created_at']
    list_filter = ['status', 'market_name', 'delivery_city']
    search_fields = ['title', 'market_name', 'delivery_address']
    readonly_fields = ['created_at', 'completed_at']
    inlines = [MarketItemInline, CoursierOfferInline]

    def get_queryset(self, request):
        return super().get_queryset(request).using('market_db')

    def save_model(self, request, obj, form, change):
        obj.save(using='market_db')


@admin.register(MarketItem)
class MarketItemAdmin(admin.ModelAdmin):
    list_display = ['name', 'quantity', 'request', 'is_found', 'actual_price']
    list_filter = ['is_found']

    def get_queryset(self, request):
        return super().get_queryset(request).using('market_db')

    def save_model(self, request, obj, form, change):
        obj.save(using='market_db')
