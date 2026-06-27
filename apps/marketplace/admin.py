from django.contrib import admin
from .models import Category, Shop, Product, MarketplaceOrder, MarketplaceOrderItem, ProductReview


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'icon', 'is_active', 'order']
    prepopulated_fields = {'slug': ('name',)}
    list_editable = ['is_active', 'order']

    def get_queryset(self, request):
        return super().get_queryset(request).using('marketplace_db')

    def save_model(self, request, obj, form, change):
        obj.save(using='marketplace_db')


class ProductInline(admin.TabularInline):
    model = Product
    extra = 0
    fields = ['name', 'price', 'stock', 'is_available', 'is_featured']


@admin.register(Shop)
class ShopAdmin(admin.ModelAdmin):
    list_display = ['name', 'city', 'category', 'is_active', 'has_delivery', 'rating', 'total_sales', 'owner_id']
    list_filter = ['is_active', 'has_delivery', 'city', 'category']
    search_fields = ['name', 'city']
    inlines = [ProductInline]

    def get_queryset(self, request):
        return super().get_queryset(request).using('marketplace_db')

    def save_model(self, request, obj, form, change):
        obj.save(using='marketplace_db')


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'shop', 'price', 'stock', 'is_available', 'is_featured', 'views_count']
    list_filter = ['is_available', 'is_featured', 'condition', 'category']
    search_fields = ['name', 'description', 'shop__name']
    list_editable = ['is_available', 'is_featured']

    def get_queryset(self, request):
        return super().get_queryset(request).using('marketplace_db')

    def save_model(self, request, obj, form, change):
        obj.save(using='marketplace_db')


class OrderItemInline(admin.TabularInline):
    model = MarketplaceOrderItem
    extra = 0
    readonly_fields = ['product', 'quantity', 'unit_price']


@admin.register(MarketplaceOrder)
class MarketplaceOrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'shop', 'client_id', 'status', 'delivery_type', 'total_price', 'created_at']
    list_filter = ['status', 'delivery_type']
    search_fields = ['id', 'delivery_address']
    readonly_fields = ['created_at', 'delivered_at']
    inlines = [OrderItemInline]

    def get_queryset(self, request):
        return super().get_queryset(request).using('marketplace_db')

    def save_model(self, request, obj, form, change):
        obj.save(using='marketplace_db')
