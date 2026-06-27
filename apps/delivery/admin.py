from django.contrib import admin
from .models import Restaurant, MenuItem, FoodCategory, DeliveryOrder, DeliveryOrderItem, DeliveryRating


class MenuItemInline(admin.TabularInline):
    model = MenuItem
    extra = 0


@admin.register(Restaurant)
class RestaurantAdmin(admin.ModelAdmin):
    list_display = ['name', 'city', 'is_open', 'rating', 'total_orders', 'owner_id']
    list_filter = ['is_open', 'city']
    search_fields = ['name', 'city']
    inlines = [MenuItemInline]
    actions = ['toggle_open']

    def toggle_open(self, request, queryset):
        for r in queryset:
            r.is_open = not r.is_open
            r.save()
    toggle_open.short_description = 'Basculer ouvert/fermé'

    def get_queryset(self, request):
        return super().get_queryset(request).using('delivery_db')

    def save_model(self, request, obj, form, change):
        obj.save(using='delivery_db')

    def delete_model(self, request, obj):
        obj.delete(using='delivery_db')


@admin.register(FoodCategory)
class FoodCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'icon']

    def get_queryset(self, request):
        return super().get_queryset(request).using('delivery_db')

    def save_model(self, request, obj, form, change):
        obj.save(using='delivery_db')


class DeliveryOrderItemInline(admin.TabularInline):
    model = DeliveryOrderItem
    extra = 0
    readonly_fields = ['menu_item', 'quantity', 'unit_price']


@admin.register(DeliveryOrder)
class DeliveryOrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'restaurant', 'client_id', 'status', 'total_price', 'created_at']
    list_filter = ['status', 'restaurant__city']
    search_fields = ['id', 'delivery_address']
    readonly_fields = ['created_at', 'confirmed_at', 'picked_up_at', 'delivered_at']
    inlines = [DeliveryOrderItemInline]

    def get_queryset(self, request):
        return super().get_queryset(request).using('delivery_db')

    def save_model(self, request, obj, form, change):
        obj.save(using='delivery_db')


@admin.register(MenuItem)
class MenuItemAdmin(admin.ModelAdmin):
    list_display = ['name', 'restaurant', 'price', 'is_available', 'is_popular']
    list_filter = ['is_available', 'is_popular', 'restaurant']
    search_fields = ['name', 'restaurant__name']

    def get_queryset(self, request):
        return super().get_queryset(request).using('delivery_db')

    def save_model(self, request, obj, form, change):
        obj.save(using='delivery_db')
