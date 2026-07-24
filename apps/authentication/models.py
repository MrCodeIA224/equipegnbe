"""
Service Authentification - Modèles utilisateurs GnExpress
Gère tous les types d'acteurs de la plateforme.
"""
from django.contrib.auth.models import AbstractUser
from django.db import models
from config.constants import GUINEA_CITIES


class OrderType(models.TextChoices):
    """
    Type de commande référencée par un modèle cross-service (PromoRedemption,
    LivreurPosition, Notification, Conversation...). Partagé pour éviter de
    redéfinir les mêmes 3 choix dans chaque modèle qui référence une commande
    par (order_type, order_id) plutôt que par FK - voir la note sur le routage
    multi-bases dans PromoRedemption ci-dessous.
    """
    DELIVERY = 'DELIVERY', 'Livraison'
    MARKET = 'MARKET', 'Mon Marché'
    MARKETPLACE = 'MARKETPLACE', 'Boutiques'


class User(AbstractUser):
    """
    Modèle utilisateur centralisé.
    Un seul compte par personne, le rôle définit les droits et l'interface.
    """

    class Role(models.TextChoices):
        ADMIN = 'ADMIN', 'Administrateur'
        CLIENT = 'CLIENT', 'Client'
        LIVREUR = 'LIVREUR', 'Livreur'
        RESTAURANT = 'RESTAURANT', 'Restaurant / Vendeur alimentaire'
        BOUTIQUIERR = 'BOUTIQUIERR', 'Boutiquierr (Marché Numérique)'
        COURSIER = 'COURSIER', 'Coursier de Marché'

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.CLIENT,
        verbose_name='Rôle'
    )
    phone = models.CharField(max_length=20, verbose_name='Téléphone')
    city = models.CharField(max_length=100, choices=GUINEA_CITIES, default='Conakry', verbose_name='Ville')
    address = models.TextField(blank=True, verbose_name='Adresse')
    profile_picture = models.ImageField(
        upload_to='profiles/', blank=True, null=True,
        verbose_name='Photo de profil'
    )
    is_verified = models.BooleanField(default=False, verbose_name='Compte vérifié')
    is_available = models.BooleanField(
        default=True,
        verbose_name='Disponible',
        help_text='Pour les livreurs et coursiers : indique la disponibilité'
    )
    bio = models.TextField(blank=True, verbose_name='Biographie / Description')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Utilisateur'
        verbose_name_plural = 'Utilisateurs'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.get_role_display()})"

    @property
    def is_admin(self):
        return self.role == self.Role.ADMIN or self.is_superuser

    @property
    def is_livreur(self):
        return self.role == self.Role.LIVREUR

    @property
    def is_coursier(self):
        return self.role == self.Role.COURSIER

    @property
    def is_restaurant(self):
        return self.role == self.Role.RESTAURANT

    @property
    def is_boutiquierr(self):
        return self.role == self.Role.BOUTIQUIERR

    @property
    def is_client(self):
        return self.role == self.Role.CLIENT


class LivreurProfile(models.Model):
    """Profil étendu pour les livreurs"""

    class VehicleType(models.TextChoices):
        MOTO = 'MOTO', 'Moto'
        VELO = 'VELO', 'Vélo'
        VOITURE = 'VOITURE', 'Voiture'
        PIED = 'PIED', 'À pied'

    user = models.OneToOneField(
        User, on_delete=models.CASCADE,
        related_name='livreur_profile'
    )
    vehicle_type = models.CharField(
        max_length=20, choices=VehicleType.choices, default=VehicleType.MOTO
    )
    license_number = models.CharField(max_length=50, blank=True, verbose_name='Numéro de permis')
    id_card = models.ImageField(upload_to='livreurs/ids/', blank=True, null=True, verbose_name="Pièce d'identité")
    total_deliveries = models.IntegerField(default=0)
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=5.00)
    zone = models.CharField(max_length=100, choices=GUINEA_CITIES, default='Conakry', verbose_name='Zone de livraison')

    class Meta:
        verbose_name = 'Profil Livreur'

    def __str__(self):
        return f"Livreur: {self.user.get_full_name()}"


class CoursierProfile(models.Model):
    """Profil étendu pour les coursiers de marché"""

    user = models.OneToOneField(
        User, on_delete=models.CASCADE,
        related_name='coursier_profile'
    )
    preferred_markets = models.CharField(
        max_length=500, blank=True,
        verbose_name='Marchés préférés',
        help_text='Ex: Madina, Cosa, Dixinn...'
    )
    total_missions = models.IntegerField(default=0)
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=5.00)
    zone = models.CharField(max_length=100, choices=GUINEA_CITIES, default='Conakry')

    class Meta:
        verbose_name = 'Profil Coursier'

    def __str__(self):
        return f"Coursier: {self.user.get_full_name()}"


class Address(models.Model):
    """Adresse sauvegardée d'un utilisateur, réutilisable lors du checkout."""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='addresses')
    label = models.CharField(max_length=50, verbose_name='Libellé', help_text='Ex: Maison, Bureau...')
    full_address = models.TextField(verbose_name='Adresse complète')
    city = models.CharField(max_length=100, choices=GUINEA_CITIES, default='Conakry', verbose_name='Ville')
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True, verbose_name='Latitude')
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True, verbose_name='Longitude')
    is_default = models.BooleanField(default=False, verbose_name='Adresse par défaut')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Adresse'
        verbose_name_plural = 'Adresses'
        ordering = ['-is_default', '-created_at']

    def __str__(self):
        return f"{self.label} ({self.user.username})"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.is_default:
            Address.objects.filter(user=self.user, is_default=True).exclude(pk=self.pk).update(is_default=False)


class LivreurPosition(models.Model):
    """
    Dernière position GPS connue d'un livreur, partagée pendant une livraison
    en cours. User et LivreurPosition vivent tous deux dans `default` : la
    OneToOneField est une vraie FK (légale, même base) - contrairement aux
    références de commandes cross-db (order_type/order_id bruts) utilisées
    ailleurs, car ici pas de traversée de base.
    """

    livreur = models.OneToOneField(User, on_delete=models.CASCADE, related_name='live_position')
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    # Informatif uniquement (debug/admin) - jamais utilisé pour une décision de permission.
    current_order_type = models.CharField(max_length=20, choices=OrderType.choices, blank=True)
    current_order_id = models.IntegerField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Position livreur'

    def __str__(self):
        return f"Position de {self.livreur.get_full_name()} ({self.updated_at:%H:%M:%S})"


class PromoCode(models.Model):
    """Code promo applicable sur les commandes livraison/marché/boutiques."""

    class DiscountType(models.TextChoices):
        PERCENTAGE = 'PERCENTAGE', 'Pourcentage'
        FIXED = 'FIXED', 'Montant fixe'

    code = models.CharField(max_length=30, unique=True, verbose_name='Code')
    discount_type = models.CharField(max_length=20, choices=DiscountType.choices, default=DiscountType.PERCENTAGE)
    value = models.DecimalField(max_digits=12, decimal_places=0, verbose_name='Valeur (% ou GNF)')
    min_order_amount = models.DecimalField(max_digits=12, decimal_places=0, default=0, verbose_name='Montant minimum de commande (GNF)')
    usage_limit = models.IntegerField(null=True, blank=True, verbose_name='Limite d\'utilisation', help_text='Vide = illimité')
    times_used = models.IntegerField(default=0)
    expiry_date = models.DateTimeField(null=True, blank=True, verbose_name='Date d\'expiration', help_text='Vide = pas d\'expiration')
    applicable_order_types = models.JSONField(
        default=list,
        verbose_name='Types de commande concernés',
        help_text='Sous-ensemble de DELIVERY, MARKET, MARKETPLACE. Vide = tous.'
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Code promo'
        verbose_name_plural = 'Codes promo'
        ordering = ['-created_at']

    def __str__(self):
        return self.code


class PromoRedemption(models.Model):
    """Trace d'utilisation d'un code promo sur une commande (cross-service)."""

    promo_code = models.ForeignKey(PromoCode, on_delete=models.CASCADE, related_name='redemptions')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='promo_redemptions')
    order_type = models.CharField(max_length=20, choices=OrderType.choices)
    # order_id est un entier brut (pas une FK) : la commande vit dans une autre
    # base (delivery_db/market_db/marketplace_db), voir config/database_router.py.
    order_id = models.IntegerField(verbose_name='ID de la commande (service concerné)')
    discount_amount = models.DecimalField(max_digits=12, decimal_places=0)
    redeemed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Utilisation de code promo'
        verbose_name_plural = 'Utilisations de codes promo'
        unique_together = ['promo_code', 'user', 'order_type', 'order_id']
        ordering = ['-redeemed_at']

    def __str__(self):
        return f"{self.promo_code.code} - {self.user.username} ({self.order_type} #{self.order_id})"


class Notification(models.Model):
    """Notification in-app pour un utilisateur, déclenchée par un événement
    métier (changement de statut, offre reçue...) dans n'importe quel service."""

    class NotificationType(models.TextChoices):
        ORDER_STATUS = 'ORDER_STATUS', 'Statut de commande'
        OFFER = 'OFFER', 'Offre'
        SYSTEM = 'SYSTEM', 'Système'

    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=200)
    message = models.TextField()
    notification_type = models.CharField(max_length=20, choices=NotificationType.choices, default=NotificationType.SYSTEM)
    # Référence cross-service en champs bruts, comme PromoRedemption.
    order_type = models.CharField(max_length=20, choices=OrderType.choices, blank=True)
    order_id = models.IntegerField(null=True, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Notification'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} → {self.recipient.username}"


class Conversation(models.Model):
    """
    Fil de discussion entre un client et l'acteur qui lui est assigné
    (livreur ou coursier) sur une commande donnée. unique_together porte sur
    (order_type, order_id, assignee) et non (order_type, order_id) seul :
    une MarketRequest a deux rôles assignés successifs (coursier pendant les
    courses, puis livreur pour la livraison finale), donc deux conversations
    distinctes légitimes peuvent exister pour la même demande.
    """

    order_type = models.CharField(max_length=20, choices=OrderType.choices)
    order_id = models.IntegerField()
    client = models.ForeignKey(User, on_delete=models.CASCADE, related_name='client_conversations')
    assignee = models.ForeignKey(User, on_delete=models.CASCADE, related_name='assigned_conversations')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Conversation'
        unique_together = ['order_type', 'order_id', 'assignee']
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.order_type} #{self.order_id} : {self.client.username} ↔ {self.assignee.username}"


class Message(models.Model):
    """Message individuel dans une Conversation."""

    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Message'
        ordering = ['created_at']

    def __str__(self):
        return f"{self.sender.username}: {self.body[:40]}"
