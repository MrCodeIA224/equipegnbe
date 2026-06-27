"""
Service Mon Marché - Module 2
Mise en relation clients / coursiers / livreurs pour faire les courses au marché.
DB: market_db
"""
from django.db import models


class MarketRequest(models.Model):
    """
    Demande de courses au marché d'un client.
    Workflow: CLIENT crée → COURSIER accepte → fait les courses → LIVREUR livre
    """

    class Status(models.TextChoices):
        OPEN = 'OPEN', 'Ouverte - En attente de coursier'
        ASSIGNED = 'ASSIGNED', 'Coursier assigné'
        SHOPPING = 'SHOPPING', 'En cours - Courses en train d\'être faites'
        NEED_DELIVERY = 'NEED_DELIVERY', 'Prête - Cherche livreur'
        DELIVERING = 'DELIVERING', 'En livraison'
        COMPLETED = 'COMPLETED', 'Terminée'
        CANCELLED = 'CANCELLED', 'Annulée'

    # Cross-service IDs
    client_id = models.IntegerField(verbose_name='ID client')
    coursier_id = models.IntegerField(null=True, blank=True, verbose_name='ID coursier')
    livreur_id = models.IntegerField(null=True, blank=True, verbose_name='ID livreur')

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN)
    title = models.CharField(max_length=200, verbose_name='Titre', default='Mes courses')
    market_name = models.CharField(max_length=200, verbose_name='Marché cible', default='Marché Madina')
    delivery_address = models.TextField(verbose_name='Adresse de livraison')
    delivery_city = models.CharField(max_length=100, default='Conakry')

    budget = models.DecimalField(
        max_digits=12, decimal_places=0, default=0,
        verbose_name='Budget courses (GNF)'
    )
    notes = models.TextField(blank=True, verbose_name='Instructions spéciales')
    is_delivery_needed = models.BooleanField(default=True, verbose_name='Livraison nécessaire')

    # Frais
    service_fee = models.DecimalField(max_digits=12, decimal_places=0, default=10000, verbose_name='Frais de service (GNF)')
    delivery_fee = models.DecimalField(max_digits=12, decimal_places=0, default=0, verbose_name='Frais de livraison (GNF)')
    actual_total = models.DecimalField(max_digits=12, decimal_places=0, default=0, verbose_name='Total réel dépensé (GNF)')

    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        app_label = 'market'
        verbose_name = 'Demande de courses'
        verbose_name_plural = 'Demandes de courses'
        ordering = ['-created_at']

    def __str__(self):
        return f"Courses #{self.id} - {self.market_name} ({self.get_status_display()})"


class MarketItem(models.Model):
    """Un article dans la liste de courses"""

    request = models.ForeignKey(MarketRequest, on_delete=models.CASCADE, related_name='items')
    name = models.CharField(max_length=200, verbose_name='Article')
    quantity = models.CharField(max_length=100, verbose_name='Quantité', help_text='Ex: 2 kg, 3 pièces, 1 botte')
    estimated_price = models.DecimalField(
        max_digits=12, decimal_places=0, null=True, blank=True,
        verbose_name='Prix estimé (GNF)'
    )
    actual_price = models.DecimalField(
        max_digits=12, decimal_places=0, null=True, blank=True,
        verbose_name='Prix réel (GNF)'
    )
    is_found = models.BooleanField(default=False, verbose_name='Trouvé au marché')
    notes = models.CharField(max_length=300, blank=True, verbose_name='Notes sur l\'article')

    class Meta:
        app_label = 'market'
        verbose_name = 'Article de courses'
        verbose_name_plural = 'Articles de courses'

    def __str__(self):
        return f"{self.quantity} {self.name}"


class CoursierOffer(models.Model):
    """Offre d'un coursier pour une demande de courses"""

    request = models.ForeignKey(MarketRequest, on_delete=models.CASCADE, related_name='offers')
    coursier_id = models.IntegerField(verbose_name='ID coursier')
    message = models.TextField(blank=True, verbose_name='Message du coursier')
    proposed_fee = models.DecimalField(
        max_digits=12, decimal_places=0, default=0,
        verbose_name='Frais de service proposés (GNF)'
    )
    is_accepted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'market'
        verbose_name = 'Offre coursier'
        unique_together = ['request', 'coursier_id']

    def __str__(self):
        return f"Offre coursier #{self.coursier_id} pour demande #{self.request_id}"


class MarketRating(models.Model):
    """Notation d'une mission de courses"""
    request = models.OneToOneField(MarketRequest, on_delete=models.CASCADE, related_name='rating')
    client_id = models.IntegerField()
    coursier_rating = models.IntegerField(default=5, choices=[(i, i) for i in range(1, 6)])
    livreur_rating = models.IntegerField(null=True, blank=True, choices=[(i, i) for i in range(1, 6)])
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'market'
        verbose_name = 'Notation courses'
