from rest_framework import viewsets, generics, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from django.utils import timezone

from .models import Restaurant, MenuItem, FoodCategory, DeliveryOrder, DeliveryOrderItem, DeliveryRating, DeliveryPayment
from .serializers import (
    RestaurantSerializer, RestaurantListSerializer, MenuItemSerializer,
    FoodCategorySerializer, DeliveryOrderSerializer, CreateDeliveryOrderSerializer,
    DeliveryRatingSerializer
)
from apps.authentication.permissions import (
    IsAdmin, IsRestaurantOrAdmin, IsLivreurOrAdmin, IsOwnerOrAdmin
)
from apps.common.payment_providers import get_provider
from apps.authentication.services import get_livreur_position, notify


class FoodCategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = FoodCategory.objects.all()
    serializer_class = FoodCategorySerializer
    permission_classes = [AllowAny]


class RestaurantViewSet(viewsets.ModelViewSet):
    serializer_class = RestaurantSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['city', 'is_open']
    search_fields = ['name', 'description', 'city']
    ordering_fields = ['rating', 'total_orders', 'name']
    ordering = ['-rating']

    def get_queryset(self):
        return Restaurant.objects.using('delivery_db').all()

    def get_serializer_class(self):
        if self.action == 'list':
            return RestaurantListSerializer
        return RestaurantSerializer

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [AllowAny()]
        if self.action == 'create':
            return [IsRestaurantOrAdmin()]
        if self.action in ['update', 'partial_update', 'destroy']:
            return [IsRestaurantOrAdmin()]
        return [IsAuthenticated()]

    def perform_create(self, serializer):
        serializer.save(owner_id=self.request.user.id)

    def get_object(self):
        obj = super().get_object()
        # Vérifier que le restaurant appartient bien à l'utilisateur (sauf admin)
        if self.action in ['update', 'partial_update', 'destroy']:
            user = self.request.user
            if not user.is_admin and obj.owner_id != user.id:
                from rest_framework.exceptions import PermissionDenied
                raise PermissionDenied("Vous n'êtes pas propriétaire de ce restaurant.")
        return obj

    @action(detail=True, methods=['get'])
    def menu(self, request, pk=None):
        """Menu complet du restaurant groupé par catégorie"""
        restaurant = self.get_object()
        categories = FoodCategory.objects.all()
        result = []
        for cat in categories:
            items = MenuItem.objects.using('delivery_db').filter(
                restaurant=restaurant, category=cat, is_available=True
            )
            if items.exists():
                result.append({
                    'category': FoodCategorySerializer(cat).data,
                    'items': MenuItemSerializer(items, many=True).data
                })
        # Articles sans catégorie
        uncategorized = MenuItem.objects.using('delivery_db').filter(
            restaurant=restaurant, category=None, is_available=True
        )
        if uncategorized.exists():
            result.append({
                'category': {'id': None, 'name': 'Autres', 'icon': '🍽️'},
                'items': MenuItemSerializer(uncategorized, many=True).data
            })
        return Response(result)

    @action(detail=True, methods=['post'])
    def toggle_open(self, request, pk=None):
        """Ouvrir/fermer le restaurant"""
        restaurant = self.get_object()
        if not request.user.is_admin and restaurant.owner_id != request.user.id:
            return Response({'error': 'Permission refusée.'}, status=403)
        restaurant.is_open = not restaurant.is_open
        restaurant.save(using='delivery_db')
        return Response({'is_open': restaurant.is_open})


class MenuItemViewSet(viewsets.ModelViewSet):
    serializer_class = MenuItemSerializer

    def get_queryset(self):
        restaurant_id = self.kwargs.get('restaurant_pk')
        return MenuItem.objects.using('delivery_db').filter(restaurant_id=restaurant_id)

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [AllowAny()]
        return [IsRestaurantOrAdmin()]

    def perform_create(self, serializer):
        restaurant_id = self.kwargs.get('restaurant_pk')
        restaurant = Restaurant.objects.using('delivery_db').get(id=restaurant_id)
        # Vérifier ownership
        if not self.request.user.is_admin and restaurant.owner_id != self.request.user.id:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Vous n'êtes pas propriétaire de ce restaurant.")
        serializer.save(restaurant=restaurant)


class DeliveryOrderViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['status', 'restaurant']
    ordering = ['-created_at']

    def get_queryset(self):
        user = self.request.user
        qs = DeliveryOrder.objects.using('delivery_db').all()

        if user.is_admin:
            return qs
        elif user.role == 'CLIENT':
            return qs.filter(client_id=user.id)
        elif user.role == 'LIVREUR':
            from django.db.models import Q
            return qs.filter(Q(livreur_id=user.id) | Q(status='READY', livreur_id=None))
        elif user.role == 'RESTAURANT':
            owned_restaurants = Restaurant.objects.using('delivery_db').filter(owner_id=user.id)
            return qs.filter(restaurant__in=owned_restaurants)
        return qs.none()

    def get_serializer_class(self):
        if self.action == 'create':
            return CreateDeliveryOrderSerializer
        return DeliveryOrderSerializer

    def create(self, request, *args, **kwargs):
        if request.user.role not in ['CLIENT', 'ADMIN']:
            return Response({'error': 'Seuls les clients peuvent passer des commandes.'}, status=403)
        serializer = CreateDeliveryOrderSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        order = serializer.save()
        notify(
            order.restaurant.owner_id, 'Nouvelle commande reçue',
            f"Commande #{order.id} - {order.items_total} GNF",
            notification_type='ORDER_STATUS', order_type='DELIVERY', order_id=order.id,
        )
        return Response(DeliveryOrderSerializer(order).data, status=201)

    @action(detail=True, methods=['post'])
    def update_status(self, request, pk=None):
        """Mise à jour du statut selon le rôle"""
        order = self.get_object()
        new_status = request.data.get('status')
        user = request.user

        # Règles de transition de statut par rôle
        allowed_transitions = {
            'RESTAURANT': {
                'PENDING': ['CONFIRMED', 'CANCELLED'],
                'CONFIRMED': ['PREPARING'],
                'PREPARING': ['READY'],
                'LIVREUR_CANCELLED': ['READY'],  # Confirme l'annulation → remet en attente de livreur
            },
            'LIVREUR': {
                'PICKED_UP': ['DELIVERING'],
                'DELIVERING': ['DELIVERED'],
            },
            'ADMIN': None,  # Admin peut tout faire
            'CLIENT': {
                'PENDING': ['CANCELLED'],
            }
        }

        role_transitions = allowed_transitions.get(user.role, {})
        if role_transitions is not None:  # None = admin, pas de restriction
            allowed = role_transitions.get(order.status, [])
            if new_status not in allowed:
                return Response(
                    {'error': f"Transition '{order.status}' → '{new_status}' non autorisée pour votre rôle."},
                    status=400
                )

        if user.role == 'RESTAURANT' and order.status == 'PENDING' and new_status == 'CONFIRMED':
            payment = getattr(order, 'payment', None)
            if not payment or payment.status != DeliveryPayment.Status.CONFIRMED:
                return Response(
                    {'error': "Paiement non confirmé — impossible d'accepter la commande."},
                    status=400
                )

        order.status = new_status
        # Timestamps automatiques
        if new_status == 'CONFIRMED':
            order.confirmed_at = timezone.now()
        elif new_status == 'PICKED_UP':
            order.picked_up_at = timezone.now()
        elif new_status == 'DELIVERED':
            order.delivered_at = timezone.now()
            # Incrémenter le compteur restaurant
            order.restaurant.total_orders += 1
            order.restaurant.save(using='delivery_db')
        elif new_status == 'READY' and user.role == 'RESTAURANT':
            # Restaurant confirme l'annulation du livreur → libérer la commande
            order.livreur_id = None

        order.save(using='delivery_db')
        if new_status == 'CONFIRMED':
            notify(
                order.client_id, 'Commande confirmée',
                f"{order.restaurant.name} a confirmé votre commande #{order.id}.",
                notification_type='ORDER_STATUS', order_type='DELIVERY', order_id=order.id,
            )
        elif new_status == 'DELIVERED':
            notify(
                order.client_id, 'Commande livrée',
                f"Votre commande #{order.id} chez {order.restaurant.name} a été livrée.",
                notification_type='ORDER_STATUS', order_type='DELIVERY', order_id=order.id,
            )
        return Response(DeliveryOrderSerializer(order).data)

    @action(detail=True, methods=['post'])
    def assign_livreur(self, request, pk=None):
        """Livreur s'assigne lui-même ou admin assigne"""
        order = self.get_object()
        user = request.user

        if user.role == 'LIVREUR':
            livreur_id = user.id
        elif user.is_admin:
            livreur_id = request.data.get('livreur_id')
            if not livreur_id:
                return Response({'error': 'livreur_id requis.'}, status=400)
        else:
            return Response({'error': 'Permission refusée.'}, status=403)

        if order.status != 'READY':
            return Response({'error': 'La commande doit être prête pour assigner un livreur.'}, status=400)

        if order.livreur_id is not None:
            return Response({'error': 'Un autre livreur a déjà pris en charge cette commande.'}, status=400)

        order.livreur_id = livreur_id
        order.status = DeliveryOrder.Status.PICKED_UP
        order.picked_up_at = timezone.now()
        order.save(using='delivery_db')
        notify(
            order.client_id, 'Livreur assigné',
            f"Un livreur a pris en charge votre commande #{order.id}.",
            notification_type='ORDER_STATUS', order_type='DELIVERY', order_id=order.id,
        )
        return Response(DeliveryOrderSerializer(order).data)

    @action(detail=True, methods=['post'], url_path='payment/initiate')
    def initiate_payment(self, request, pk=None):
        """Démarre un paiement Mobile Money simulé (Orange Money / MTN MoMo)."""
        order = self.get_object()
        user = request.user
        if not user.is_admin and order.client_id != user.id:
            return Response({'error': 'Permission refusée.'}, status=403)

        payment = getattr(order, 'payment', None)
        if not payment:
            return Response({'error': 'Aucun paiement associé à cette commande.'}, status=400)
        if payment.method == DeliveryPayment.Method.CASH_ON_DELIVERY:
            return Response({'error': 'Cette commande est payée à la livraison.'}, status=400)
        if payment.status == DeliveryPayment.Status.CONFIRMED:
            return Response({'error': 'Ce paiement est déjà confirmé.'}, status=400)

        phone = request.data.get('phone_number', payment.phone_number)
        provider = get_provider(payment.method)
        result = provider.initiate(phone, order.total_price)

        payment.phone_number = phone
        payment.transaction_reference = result.transaction_reference
        payment.otp_code = result.otp_code
        payment.status = DeliveryPayment.Status.PENDING
        payment.initiated_at = timezone.now()
        payment.save(using='delivery_db')

        return Response({
            'transaction_reference': result.transaction_reference,
            'simulated_otp': result.otp_code,
            'message': f"Code envoyé par SMS (simulation {provider.display_name}).",
        })

    @action(detail=True, methods=['post'], url_path='payment/confirm')
    def confirm_payment(self, request, pk=None):
        """Confirme le paiement Mobile Money via le code OTP simulé."""
        order = self.get_object()
        user = request.user
        if not user.is_admin and order.client_id != user.id:
            return Response({'error': 'Permission refusée.'}, status=403)

        payment = getattr(order, 'payment', None)
        if not payment or not payment.transaction_reference:
            return Response({'error': 'Aucun paiement en cours pour cette commande.'}, status=400)
        if payment.status == DeliveryPayment.Status.CONFIRMED:
            return Response({'error': 'Ce paiement est déjà confirmé.'}, status=400)

        reference = request.data.get('reference')
        otp_code = request.data.get('otp_code', '')
        if reference != payment.transaction_reference:
            return Response({'error': 'Référence de transaction invalide.'}, status=400)

        provider = get_provider(payment.method)
        result = provider.confirm(otp_code, payment.otp_code)

        if result.success:
            payment.status = DeliveryPayment.Status.CONFIRMED
            payment.confirmed_at = timezone.now()
            payment.save(using='delivery_db')
            return Response(DeliveryOrderSerializer(order).data)

        payment.failed_attempts += 1
        if payment.failed_attempts >= 3:
            payment.status = DeliveryPayment.Status.FAILED
        payment.save(using='delivery_db')
        return Response({'error': 'Code de confirmation incorrect.'}, status=400)

    @action(detail=True, methods=['post'])
    def cancel_delivery(self, request, pk=None):
        """Livreur annule la prise en charge — le restaurant doit confirmer"""
        order = self.get_object()
        user = request.user

        if user.role != 'LIVREUR' and not user.is_admin:
            return Response({'error': 'Réservé aux livreurs.'}, status=403)

        if not user.is_admin and order.livreur_id != user.id:
            return Response({'error': 'Ce n\'est pas votre livraison.'}, status=403)

        if order.status != 'PICKED_UP':
            return Response({'error': 'Impossible d\'annuler depuis cet état.'}, status=400)

        order.status = DeliveryOrder.Status.LIVREUR_CANCELLED
        order.save(using='delivery_db')
        notify(
            order.restaurant.owner_id, 'Livraison annulée par le livreur',
            f"Le livreur a annulé la commande #{order.id} — confirmation requise.",
            notification_type='ORDER_STATUS', order_type='DELIVERY', order_id=order.id,
        )
        return Response(DeliveryOrderSerializer(order).data)

    @action(detail=True, methods=['get'], url_path='livreur-position')
    def livreur_position(self, request, pk=None):
        """Position GPS du livreur assigné à cette commande (scopée via get_queryset)."""
        order = self.get_object()
        if not order.livreur_id:
            return Response({'error': 'Aucun livreur assigné.'}, status=400)
        position = get_livreur_position(order.livreur_id)
        if not position:
            return Response(None)
        return Response(position)

    @action(detail=False, methods=['get'])
    def available(self, request):
        """Commandes prêtes à être récupérées - pour les livreurs"""
        if request.user.role not in ['LIVREUR', 'ADMIN']:
            return Response({'error': 'Permission refusée.'}, status=403)
        orders = DeliveryOrder.objects.using('delivery_db').filter(
            status='READY', livreur_id=None
        )
        return Response(DeliveryOrderSerializer(orders, many=True).data)

    @action(detail=False, methods=['get'])
    def admin_all(self, request):
        """Toutes les commandes - admin uniquement"""
        if not request.user.is_admin:
            return Response({'error': 'Admin requis.'}, status=403)
        orders = DeliveryOrder.objects.using('delivery_db').all()
        page = self.paginate_queryset(orders)
        if page is not None:
            return self.get_paginated_response(DeliveryOrderSerializer(page, many=True).data)
        return Response(DeliveryOrderSerializer(orders, many=True).data)


class AdminDeliveryStatsView(generics.GenericAPIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        from django.db.models import Count, Sum
        orders = DeliveryOrder.objects.using('delivery_db')
        stats = {
            'total_orders': orders.count(),
            'pending': orders.filter(status='PENDING').count(),
            'delivering': orders.filter(status='DELIVERING').count(),
            'delivered': orders.filter(status='DELIVERED').count(),
            'cancelled': orders.filter(status='CANCELLED').count(),
            'total_restaurants': Restaurant.objects.using('delivery_db').count(),
            'open_restaurants': Restaurant.objects.using('delivery_db').filter(is_open=True).count(),
            'revenue': str(orders.filter(status='DELIVERED').aggregate(
                total=Sum('total_price'))['total'] or 0),
        }
        return Response(stats)
