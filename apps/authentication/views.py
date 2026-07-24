from rest_framework import generics, viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import RefreshToken
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from django.db.models import Q

from .models import (
    User, LivreurProfile, CoursierProfile, Address, PromoCode, PromoRedemption,
    LivreurPosition, Notification, Conversation, Message,
)
from .serializers import (
    CustomTokenObtainPairSerializer, RegisterSerializer, UserSerializer,
    ChangePasswordSerializer, AdminUserSerializer, LivreurPublicSerializer,
    LivreurProfileSerializer, CoursierProfileSerializer, UserPublicSerializer,
    AddressSerializer, PromoCodeSerializer, PromoRedemptionSerializer,
    LivreurPositionSerializer, NotificationSerializer, ConversationSerializer, MessageSerializer,
)
from .permissions import IsAdmin, IsOwnerOrAdmin, IsLivreurOrAdmin, IsConversationParticipant
from .services import validate_and_apply_promo, open_conversation, validate_order_reference


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


class AddressViewSet(viewsets.ModelViewSet):
    """Adresses sauvegardées de l'utilisateur connecté (carnet d'adresses)."""
    serializer_class = AddressSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Address.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class PromoCodeValidateView(generics.GenericAPIView):
    """
    Prévisualisation d'un code promo au checkout (sans effet de bord).
    La validation réelle + le décompte d'utilisation se refont côté serializer
    de création de commande - ne jamais faire confiance à cette preview seule.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        code = request.data.get('code', '')
        order_type = request.data.get('order_type', '')
        subtotal = request.data.get('subtotal', 0)
        result = validate_and_apply_promo(code, request.user, order_type, subtotal)
        return Response({
            'valid': True,
            'discount_amount': result['discount_amount'],
            'message': f"Code appliqué : -{result['discount_amount']:.0f} GNF",
        })


class PromoCodeViewSet(viewsets.ModelViewSet):
    """CRUD des codes promo - Admin uniquement."""
    serializer_class = PromoCodeSerializer
    permission_classes = [IsAdmin]
    queryset = PromoCode.objects.all()

    @action(detail=True, methods=['post'])
    def toggle_active(self, request, pk=None):
        promo = self.get_object()
        promo.is_active = not promo.is_active
        promo.save()
        return Response({'is_active': promo.is_active})


class PromoRedemptionViewSet(viewsets.ReadOnlyModelViewSet):
    """Historique d'utilisation des codes promo - Admin uniquement (reporting)."""
    serializer_class = PromoRedemptionSerializer
    permission_classes = [IsAdmin]
    queryset = PromoRedemption.objects.select_related('promo_code', 'user').all()


class LivreurPositionUpdateView(generics.GenericAPIView):
    """Le livreur pousse sa position GPS courante (upsert)."""
    permission_classes = [IsLivreurOrAdmin]

    def post(self, request):
        latitude = request.data.get('latitude')
        longitude = request.data.get('longitude')
        if latitude is None or longitude is None:
            return Response({'error': 'latitude et longitude requis.'}, status=400)

        order_type = request.data.get('order_type', '')
        order_id = request.data.get('order_id')
        if order_type or order_id:
            if not (order_type and order_id):
                return Response({'error': 'order_type et order_id doivent être fournis ensemble.'}, status=400)
            validate_order_reference(order_type, order_id)

        livreur_id = request.data.get('livreur_id') if request.user.is_admin else request.user.id
        LivreurPosition.objects.update_or_create(
            livreur_id=livreur_id,
            defaults={
                'latitude': latitude,
                'longitude': longitude,
                'current_order_type': request.data.get('order_type', ''),
                'current_order_id': request.data.get('order_id'),
            },
        )
        return Response({'message': 'Position mise à jour.'})


class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    """Notifications de l'utilisateur connecté."""
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(recipient=self.request.user)

    @action(detail=False, methods=['get'])
    def unread_count(self, request):
        count = self.get_queryset().filter(is_read=False).count()
        return Response({'unread_count': count})

    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        notification = self.get_object()
        notification.is_read = True
        notification.save()
        return Response({'is_read': True})

    @action(detail=False, methods=['post'])
    def mark_all_read(self, request):
        updated = self.get_queryset().filter(is_read=False).update(is_read=True)
        return Response({'updated': updated})


class ConversationOpenView(generics.GenericAPIView):
    """Ouvre (ou récupère) la conversation client↔assigné d'une commande."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        order_type = request.data.get('order_type')
        order_id = request.data.get('order_id')
        if not order_type or not order_id:
            return Response({'error': 'order_type et order_id requis.'}, status=400)

        conversation = open_conversation(order_type, order_id, request.user.id)
        return Response(ConversationSerializer(conversation).data)


class MessageViewSet(viewsets.ModelViewSet):
    """Messages d'une conversation - lecture/écriture réservées aux participants."""
    serializer_class = MessageSerializer
    permission_classes = [IsAuthenticated, IsConversationParticipant]
    http_method_names = ['get', 'post']

    def get_queryset(self):
        conversation_id = self.kwargs.get('conversation_pk')
        return Message.objects.filter(conversation_id=conversation_id).select_related('sender')

    def get_conversation(self):
        from django.shortcuts import get_object_or_404
        conversation = get_object_or_404(Conversation, id=self.kwargs.get('conversation_pk'))
        self.check_object_permissions(self.request, conversation)
        return conversation

    def list(self, request, *args, **kwargs):
        self.get_conversation()
        return super().list(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        conversation = self.get_conversation()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(conversation=conversation, sender=request.user)
        return Response(serializer.data, status=201)
