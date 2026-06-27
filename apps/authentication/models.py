"""
Service Authentification - Modèles utilisateurs GnExpress
Gère tous les types d'acteurs de la plateforme.
"""
from django.contrib.auth.models import AbstractUser
from django.db import models


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
    city = models.CharField(max_length=100, default='Conakry', verbose_name='Ville')
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
    zone = models.CharField(max_length=100, default='Conakry', verbose_name='Zone de livraison')

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
    zone = models.CharField(max_length=100, default='Conakry')

    class Meta:
        verbose_name = 'Profil Coursier'

    def __str__(self):
        return f"Coursier: {self.user.get_full_name()}"
