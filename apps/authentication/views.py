from rest_framework import generics, viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import RefreshToken
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from django.db.models import Q

from .models import User, LivreurProfile, CoursierProfile
from .serializers import (
    CustomTokenObtainPairSerializer, RegisterSerializer, UserSerializer,
    ChangePasswordSerializer, AdminUserSerializer, LivreurPublicSerializer,
    LivreurProfileSerializer, CoursierProfileSerializer, UserPublicSerializer
)
from .permissions import IsAdmin, IsOwnerOrAdmin


class LoginView(TokenObtainPairView):
    """Connexion - retourne access + refresh tokens + infos user"""
    serializer_class = CustomTokenObtainPairSerializer
    permission_classes = [AllowAny]


class RegisterView(generics.CreateAPIView):
    """Inscription d'un nouvel utilisateur"""
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        # Retourner les tokens immédiatement
        refresh = RefreshToken.for_user(user)
        return Response({
            'message': 'Compte créé avec succès.',
            'user': UserSerializer(user).data,
            'tokens': {
                'access': str(refresh.access_token),
                'refresh': str(refresh),
            }
        }, status=status.HTTP_201_CREATED)


class MeView(generics.RetrieveUpdateAPIView):
    """Profil de l'utilisateur connecté"""
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user


class ChangePasswordView(generics.UpdateAPIView):
    serializer_class = ChangePasswordSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user

    def update(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = self.get_object()
        user.set_password(serializer.validated_data['new_password'])
        user.save()
        return Response({'message': 'Mot de passe modifié avec succès.'})


class LogoutView(generics.GenericAPIView):
    """Déconnexion - invalide le refresh token"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data.get('refresh')
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response({'message': 'Déconnexion réussie.'})
        except Exception:
            return Response({'error': 'Token invalide.'}, status=status.HTTP_400_BAD_REQUEST)


class LivreurListView(generics.ListAPIView):
    """
    Liste des livreurs disponibles - accessible par clients, coursiers, boutiquierrs.
    Point de communication inter-services.
    """
    serializer_class = LivreurPublicSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['city', 'is_available']
    search_fields = ['first_name', 'last_name', 'city']

    def get_queryset(self):
        return User.objects.filter(
            role=User.Role.LIVREUR,
            is_active=True,
            is_available=True
        ).select_related('livreur_profile')


class AdminUserViewSet(viewsets.ModelViewSet):
    """
    CRUD complet des utilisateurs - Admin uniquement.
    Permet de gérer tous les acteurs de la plateforme.
    """
    serializer_class = AdminUserSerializer
    permission_classes = [IsAdmin]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['role', 'is_active', 'is_verified', 'city']
    search_fields = ['username', 'email', 'first_name', 'last_name', 'phone']
    ordering_fields = ['created_at', 'username', 'role']
    ordering = ['-created_at']

    def get_queryset(self):
        return User.objects.all().select_related('livreur_profile', 'coursier_profile')

    @action(detail=True, methods=['post'])
    def toggle_verify(self, request, pk=None):
        """Vérifier / dé-vérifier un compte"""
        user = self.get_object()
        user.is_verified = not user.is_verified
        user.save()
        status_msg = 'vérifié' if user.is_verified else 'non vérifié'
        return Response({'message': f'Compte {status_msg}.', 'is_verified': user.is_verified})

    @action(detail=True, methods=['post'])
    def toggle_active(self, request, pk=None):
        """Activer / désactiver un compte"""
        user = self.get_object()
        user.is_active = not user.is_active
        user.save()
        status_msg = 'activé' if user.is_active else 'désactivé'
        return Response({'message': f'Compte {status_msg}.', 'is_active': user.is_active})

    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Statistiques globales des utilisateurs"""
        from django.db.models import Count
        stats = User.objects.values('role').annotate(count=Count('id'))
        result = {s['role']: s['count'] for s in stats}
        result['total'] = User.objects.count()
        result['active'] = User.objects.filter(is_active=True).count()
        result['verified'] = User.objects.filter(is_verified=True).count()
        result['livreurs_available'] = User.objects.filter(
            role='LIVREUR', is_available=True, is_active=True
        ).count()
        return Response(result)
