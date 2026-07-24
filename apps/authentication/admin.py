from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, LivreurProfile, CoursierProfile, Address, PromoCode, PromoRedemption


class LivreurProfileInline(admin.StackedInline):
    model = LivreurProfile
    can_delete = False
    verbose_name_plural = 'Profil Livreur'


class CoursierProfileInline(admin.StackedInline):
    model = CoursierProfile
    can_delete = False
    verbose_name_plural = 'Profil Coursier'


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = [
        'username', 'email', 'get_full_name', 'role', 'phone',
        'city', 'is_verified', 'is_available', 'is_active', 'created_at'
    ]
    list_filter = ['role', 'is_verified', 'is_active', 'is_available', 'city']
    search_fields = ['username', 'email', 'first_name', 'last_name', 'phone']
    ordering = ['-created_at']
    readonly_fields = ['created_at', 'updated_at']

    fieldsets = UserAdmin.fieldsets + (
        ('Informations GnExpress', {
            'fields': ('role', 'phone', 'city', 'address', 'bio',
                       'profile_picture', 'is_verified', 'is_available',
                       'created_at', 'updated_at')
        }),
    )

    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Informations GnExpress', {
            'fields': ('role', 'phone', 'city', 'email', 'first_name', 'last_name')
        }),
    )

    def get_inlines(self, request, obj=None):
        if obj:
            if obj.role == 'LIVREUR':
                return [LivreurProfileInline]
            elif obj.role == 'COURSIER':
                return [CoursierProfileInline]
        return []

    actions = ['verify_users', 'unverify_users', 'activate_users', 'deactivate_users']

    def verify_users(self, request, queryset):
        queryset.update(is_verified=True)
        self.message_user(request, f'{queryset.count()} compte(s) vérifiés.')
    verify_users.short_description = 'Vérifier les comptes sélectionnés'

    def unverify_users(self, request, queryset):
        queryset.update(is_verified=False)
        self.message_user(request, f'{queryset.count()} compte(s) non vérifiés.')
    unverify_users.short_description = 'Retirer la vérification'

    def activate_users(self, request, queryset):
        queryset.update(is_active=True)
    activate_users.short_description = 'Activer les comptes sélectionnés'

    def deactivate_users(self, request, queryset):
        queryset.update(is_active=False)
    deactivate_users.short_description = 'Désactiver les comptes sélectionnés'


@admin.register(LivreurProfile)
class LivreurProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'vehicle_type', 'zone', 'rating', 'total_deliveries']
    list_filter = ['vehicle_type', 'zone']


@admin.register(CoursierProfile)
class CoursierProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'zone', 'rating', 'total_missions']


@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ['user', 'label', 'city', 'is_default', 'created_at']
    list_filter = ['city', 'is_default']
    search_fields = ['user__username', 'label', 'full_address']


@admin.register(PromoCode)
class PromoCodeAdmin(admin.ModelAdmin):
    list_display = ['code', 'discount_type', 'value', 'times_used', 'usage_limit', 'is_active', 'expiry_date']
    list_filter = ['discount_type', 'is_active']
    search_fields = ['code']


@admin.register(PromoRedemption)
class PromoRedemptionAdmin(admin.ModelAdmin):
    list_display = ['promo_code', 'user', 'order_type', 'order_id', 'discount_amount', 'redeemed_at']
    list_filter = ['order_type']
    search_fields = ['promo_code__code', 'user__username']
