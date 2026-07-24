"""
Service Marché Numérique - Module 3
Marketplace pour boutiquiers et particuliers.
DB: marketplace_db
"""
from django.db import models
from config.constants import GUINEA_CITIES


class Category(models.Model):
    """Catégorie de produits du marketplace"""
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=10, default='🛍️')
    image = models.ImageField(upload_to='categories/', blank=True, null=True)
    is_active = models.BooleanField(default=True)
    order = models.IntegerField(default=0, help_text='Ordre d\'affichage')

    class Meta:
        app_label = 'marketplace'
        verbose_name = 'Catégorie'
        ordering = ['order', 'name']

    def __str__(self):
        return self.name


class Shop(models.Model):
    """Boutique sur le marketplace"""

    # Cross-service ID
    owner_id = models.IntegerField(verbose_name='ID propriétaire')

    name = models.CharField(max_length=200, verbose_name='Nom de la boutique')
    description = models.TextField(verbose_name='Description')
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name='shops')
    address = models.CharField(max_length=300)
    city = models.CharField(max_length=100, choices=GUINEA_CITIES, default='Conakry')
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True, verbose_name='Latitude')
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True, verbose_name='Longitude')
    phone = models.CharField(max_length=20)
    whatsapp = models.CharField(max_length=20, blank=True)
    image = models.ImageField(upload_to='shops/', blank=True, null=True)
    banner = models.ImageField(upload_to='shops/banners/', blank=True, null=True)
    is_active = models.BooleanField(default=True)
    has_delivery = models.BooleanField(default=False, verbose_name='Propose la livraison')
    delivery_fee = models.DecimalField(max_digits=12, decimal_places=0, default=0)
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=5.00)
    total_sales = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'marketplace'
        verbose_name = 'Boutique'
        ordering = ['-rating', 'name']

    def __str__(self):
        return self.name


class Product(models.Model):
    """Produit dans une boutique"""

    class Condition(models.TextChoices):
        NEW = 'NEW', 'Neuf'
        USED_GOOD = 'USED_GOOD', 'Occasion - Bon état'
        USED_FAIR = 'USED_FAIR', 'Occasion - État correct'

    shop = models.ForeignKey(Shop, on_delete=models.CASCADE, related_name='products')
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name='products')
    name = models.CharField(max_length=200, verbose_name='Nom du produit')
    description = models.TextField()
    price = models.DecimalField(max_digits=12, decimal_places=0, verbose_name='Prix (GNF)')
    stock = models.IntegerField(default=0, verbose_name='Stock disponible')
    condition = models.CharField(max_length=20, choices=Condition.choices, default=Condition.NEW)
    image = models.ImageField(upload_to='products/', blank=True, null=True)
    image2 = models.ImageField(upload_to='products/', blank=True, null=True)
    image3 = models.ImageField(upload_to='products/', blank=True, null=True)
    is_available = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False, verbose_name='Mis en avant')
    has_delivery = models.BooleanField(default=False)
    views_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'marketplace'
        verbose_name = 'Produit'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} - {self.shop.name}"


class MarketplaceOrder(models.Model):
    """Commande sur le marketplace"""

    class Status(models.TextChoices):
        PENDING = 'PENDING', 'En attente de confirmation'
        CONFIRMED = 'CONFIRMED', 'Confirmée par la boutique'
        PROCESSING = 'PROCESSING', 'En préparation'
        READY = 'READY', 'Prête'
        DELIVERING = 'DELIVERING', 'En livraison'
        DELIVERED = 'DELIVERED', 'Livrée'
        PICKUP_READY = 'PICKUP_READY', 'Prête pour retrait'
        CANCELLED = 'CANCELLED', 'Annulée'
        LIVREUR_CANCELLED = 'LIVREUR_CANCELLED', 'Annulée par le livreur (confirmation requise)'

    # Cross-service IDs
    client_id = models.IntegerField()
    livreur_id = models.IntegerField(null=True, blank=True)

    shop = models.ForeignKey(Shop, on_delete=models.CASCADE, related_name='orders')
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    delivery_type = models.CharField(
        max_length=20,
        choices=[('DELIVERY', 'Livraison'), ('PICKUP', 'Retrait en boutique')],
        default='DELIVERY'
    )
    delivery_address = models.TextField(blank=True)
    delivery_city = models.CharField(max_length=100, choices=GUINEA_CITIES, default='Conakry')
    notes = models.TextField(blank=True)

    items_total = models.DecimalField(max_digits=12, decimal_places=0, default=0)
    delivery_fee = models.DecimalField(max_digits=12, decimal_places=0, default=0)
    promo_code_used = models.CharField(max_length=30, blank=True, verbose_name='Code promo utilisé')
    discount_amount = models.DecimalField(max_digits=12, decimal_places=0, default=0, verbose_name='Réduction (GNF)')
    total_price = models.DecimalField(max_digits=12, decimal_places=0, default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    delivered_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        app_label = 'marketplace'
        verbose_name = 'Commande marketplace'
        ordering = ['-created_at']

    def __str__(self):
        return f"Commande #{self.id} - {self.shop.name} ({self.get_status_display()})"


class MarketplaceOrderItem(models.Model):
    order = models.ForeignKey(MarketplaceOrder, on_delete=models.CASCADE, related_name='order_items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.IntegerField(default=1)
    unit_price = models.DecimalField(max_digits=12, decimal_places=0)

    class Meta:
        app_label = 'marketplace'

    @property
    def subtotal(self):
        return self.unit_price * self.quantity


class MarketplacePayment(models.Model):
    """Paiement (simulé) associé à une commande marketplace."""

    class Method(models.TextChoices):
        ORANGE_MONEY = 'ORANGE_MONEY', 'Orange Money'
        MTN_MOMO = 'MTN_MOMO', 'MTN Mobile Money'
        CASH_ON_DELIVERY = 'CASH_ON_DELIVERY', 'Paiement à la livraison'

    class Status(models.TextChoices):
        PENDING = 'PENDING', 'En attente'
        CONFIRMED = 'CONFIRMED', 'Confirmé'
        FAILED = 'FAILED', 'Échoué'

    order = models.OneToOneField(MarketplaceOrder, on_delete=models.CASCADE, related_name='payment')
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
        app_label = 'marketplace'
        verbose_name = 'Paiement marketplace'

    def __str__(self):
        return f"Paiement #{self.order_id} - {self.get_method_display()} ({self.get_status_display()})"


class ProductReview(models.Model):
    """Avis sur un produit"""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews')
    client_id = models.IntegerField()
    rating = models.IntegerField(choices=[(i, i) for i in range(1, 6)])
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'marketplace'
        unique_together = ['product', 'client_id']
        verbose_name = 'Avis produit'
