"""
Service Livraison - Module 1
Livraison de restauration et marchandises.
DB: delivery_db
Communication cross-service: les IDs d'utilisateurs référencent la db_auth.
"""
from django.db import models
from django.conf import settings
from config.constants import GUINEA_CITIES


class FoodCategory(models.Model):
    """Catégorie de plats (Grillades, Riz, Boissons, etc.)"""
    name = models.CharField(max_length=100)
    icon = models.CharField(max_length=10, default='🍽️')

    class Meta:
        app_label = 'delivery'
        verbose_name = 'Catégorie de plats'
        verbose_name_plural = 'Catégories de plats'
        ordering = ['name']

    def __str__(self):
        return self.name


class Restaurant(models.Model):
    """Restaurant ou vendeur alimentaire"""

    # Référence cross-service : owner_id pointe vers User.id dans db_auth
    owner_id = models.IntegerField(verbose_name='ID du propriétaire (auth service)')

    name = models.CharField(max_length=200, verbose_name='Nom')
    description = models.TextField(verbose_name='Description')
    address = models.CharField(max_length=300, verbose_name='Adresse')
    city = models.CharField(max_length=100, choices=GUINEA_CITIES, default='Conakry')
    phone = models.CharField(max_length=20)
    image = models.ImageField(upload_to='restaurants/', blank=True, null=True)
    banner = models.ImageField(upload_to='restaurants/banners/', blank=True, null=True)
    is_open = models.BooleanField(default=True, verbose_name='Ouvert')
    delivery_time_min = models.IntegerField(default=20, help_text='Temps de livraison minimum (min)')
    delivery_time_max = models.IntegerField(default=45, help_text='Temps de livraison maximum (min)')
    min_order = models.DecimalField(max_digits=12, decimal_places=0, default=0, verbose_name='Commande minimum (GNF)')
    delivery_fee = models.DecimalField(max_digits=12, decimal_places=0, default=5000)
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=5.00)
    total_orders = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'delivery'
        verbose_name = 'Restaurant'
        ordering = ['-rating', 'name']

    def __str__(self):
        return self.name

    @property
    def delivery_time(self):
        return f"{self.delivery_time_min}-{self.delivery_time_max} min"


class MenuItem(models.Model):
    """Plat ou article dans le menu d'un restaurant"""

    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name='menu_items')
    category = models.ForeignKey(FoodCategory, on_delete=models.SET_NULL, null=True, blank=True)
    name = models.CharField(max_length=200, verbose_name='Nom du plat')
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=12, decimal_places=0, verbose_name='Prix (GNF)')
    image = models.ImageField(upload_to='menu_items/', blank=True, null=True)
    is_available = models.BooleanField(default=True, verbose_name='Disponible')
    is_popular = models.BooleanField(default=False, verbose_name='Populaire')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'delivery'
        verbose_name = 'Plat / Article menu'
        verbose_name_plural = 'Plats / Articles menu'
        ordering = ['category', 'name']

    def __str__(self):
        return f"{self.name} - {self.restaurant.name}"


class DeliveryOrder(models.Model):
    """Commande de livraison"""

    class Status(models.TextChoices):
        PENDING = 'PENDING', 'En attente de confirmation'
        CONFIRMED = 'CONFIRMED', 'Confirmée'
        PREPARING = 'PREPARING', 'En préparation'
        READY = 'READY', 'Prête pour livraison'
        PICKED_UP = 'PICKED_UP', 'Prise en charge par le livreur'
        DELIVERING = 'DELIVERING', 'En livraison'
        DELIVERED = 'DELIVERED', 'Livrée'
        CANCELLED = 'CANCELLED', 'Annulée'
        LIVREUR_CANCELLED = 'LIVREUR_CANCELLED', 'Annulée par le livreur (confirmation requise)'

    # Cross-service IDs
    client_id = models.IntegerField(verbose_name='ID client')
    livreur_id = models.IntegerField(null=True, blank=True, verbose_name='ID livreur')

    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name='orders')
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    delivery_address = models.TextField(verbose_name='Adresse de livraison')
    delivery_city = models.CharField(max_length=100, choices=GUINEA_CITIES, default='Conakry')
    notes = models.TextField(blank=True, verbose_name='Instructions spéciales')

    items_total = models.DecimalField(max_digits=12, decimal_places=0, default=0)
    delivery_fee = models.DecimalField(max_digits=12, decimal_places=0, default=0)
    promo_code_used = models.CharField(max_length=30, blank=True, verbose_name='Code promo utilisé')
    discount_amount = models.DecimalField(max_digits=12, decimal_places=0, default=0, verbose_name='Réduction (GNF)')
    total_price = models.DecimalField(max_digits=12, decimal_places=0, default=0)

    # Timestamps pour tracking
    created_at = models.DateTimeField(auto_now_add=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    picked_up_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        app_label = 'delivery'
        verbose_name = 'Commande livraison'
        verbose_name_plural = 'Commandes livraison'
        ordering = ['-created_at']

    def __str__(self):
        return f"Commande #{self.id} - {self.restaurant.name} ({self.get_status_display()})"

    def calculate_total(self):
        self.items_total = sum(
            item.unit_price * item.quantity for item in self.order_items.all()
        )
        self.total_price = self.items_total + self.delivery_fee
        self.save()


class DeliveryOrderItem(models.Model):
    order = models.ForeignKey(DeliveryOrder, on_delete=models.CASCADE, related_name='order_items')
    menu_item = models.ForeignKey(MenuItem, on_delete=models.CASCADE)
    quantity = models.IntegerField(default=1)
    unit_price = models.DecimalField(max_digits=12, decimal_places=0)
    notes = models.CharField(max_length=200, blank=True)

    class Meta:
        app_label = 'delivery'

    def __str__(self):
        return f"{self.quantity}x {self.menu_item.name}"

    @property
    def subtotal(self):
        return self.unit_price * self.quantity


class DeliveryPayment(models.Model):
    """Paiement (simulé) associé à une commande de livraison."""

    class Method(models.TextChoices):
        ORANGE_MONEY = 'ORANGE_MONEY', 'Orange Money'
        MTN_MOMO = 'MTN_MOMO', 'MTN Mobile Money'
        CASH_ON_DELIVERY = 'CASH_ON_DELIVERY', 'Paiement à la livraison'

    class Status(models.TextChoices):
        PENDING = 'PENDING', 'En attente'
        CONFIRMED = 'CONFIRMED', 'Confirmé'
        FAILED = 'FAILED', 'Échoué'

    order = models.OneToOneField(DeliveryOrder, on_delete=models.CASCADE, related_name='payment')
    method = models.CharField(max_length=20, choices=Method.choices, default=Method.CASH_ON_DELIVERY)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    phone_number = models.CharField(max_length=20, blank=True)
    transaction_reference = models.CharField(max_length=64, blank=True)
    otp_code = models.CharField(max_length=10, blank=True, verbose_name='Code de confirmation (simulation)')
    failed_attempts = models.IntegerField(default=0)
    initiated_at = models.DateTimeField(null=True, blank=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'delivery'
        verbose_name = 'Paiement livraison'

    def __str__(self):
        return f"Paiement #{self.order_id} - {self.get_method_display()} ({self.get_status_display()})"


class DeliveryRating(models.Model):
    """Notation d'une livraison"""
    order = models.OneToOneField(DeliveryOrder, on_delete=models.CASCADE, related_name='rating')
    client_id = models.IntegerField()
    restaurant_rating = models.IntegerField(default=5, choices=[(i, i) for i in range(1, 6)])
    livreur_rating = models.IntegerField(default=5, choices=[(i, i) for i in range(1, 6)])
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'delivery'
        verbose_name = 'Notation livraison'
