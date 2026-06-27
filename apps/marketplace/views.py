from rest_framework import viewsets, generics, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from django.utils import timezone

from .models import Category, Shop, Product, MarketplaceOrder, MarketplaceOrderItem, ProductReview
from .serializers import (
    CategorySerializer, ShopSerializer, ShopListSerializer, ProductSerializer,
    MarketplaceOrderSerializer, CreateMarketplaceOrderSerializer,
    ProductReviewSerializer
)
from apps.authentication.permissions import IsAdmin, IsBoutiquierrOrAdmin, IsLivreurOrAdmin


class CategoryViewSet(viewsets.ModelViewSet):
    serializer_class = CategorySerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        return Category.objects.using('marketplace_db').filter(is_active=True)

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [AllowAny()]
        return [IsAdmin()]


class ShopViewSet(viewsets.ModelViewSet):
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['city', 'is_active', 'has_delivery', 'category']
    search_fields = ['name', 'description', 'city']
    ordering_fields = ['rating', 'total_sales', 'name', 'created_at']
    ordering = ['-rating']

    def get_queryset(self):
        return Shop.objects.using('marketplace_db').all()

    def get_serializer_class(self):
        if self.action == 'list':
            return ShopListSerializer
        return ShopSerializer

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [AllowAny()]
        if self.action == 'create':
            return [IsBoutiquierrOrAdmin()]
        return [IsAuthenticated()]

    def perform_create(self, serializer):
        serializer.save(owner_id=self.request.user.id)

    def get_object(self):
        obj = super().get_object()
        if self.action in ['update', 'partial_update', 'destroy']:
            user = self.request.user
            if not user.is_admin and obj.owner_id != user.id:
                from rest_framework.exceptions import PermissionDenied
                raise PermissionDenied("Vous n'êtes pas propriétaire de cette boutique.")
        return obj

    @action(detail=True, methods=['get'])
    def products(self, request, pk=None):
        shop = self.get_object()
        category_id = request.query_params.get('category')
        qs = Product.objects.using('marketplace_db').filter(shop=shop, is_available=True)
        if category_id:
            qs = qs.filter(category_id=category_id)
        return Response(ProductSerializer(qs, many=True).data)


class ProductViewSet(viewsets.ModelViewSet):
    serializer_class = ProductSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['category', 'is_available', 'has_delivery', 'condition', 'shop__city']
    search_fields = ['name', 'description']
    ordering_fields = ['price', 'created_at', 'views_count']
    ordering = ['-created_at']

    def get_queryset(self):
        return Product.objects.using('marketplace_db').filter(is_available=True)

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [AllowAny()]
        return [IsBoutiquierrOrAdmin()]

    def retrieve(self, request, *args, **kwargs):
        product = self.get_object()
        # Incrémenter les vues
        product.views_count += 1
        product.save(using='marketplace_db')
        return Response(ProductSerializer(product).data)

    def perform_create(self, serializer):
        user = self.request.user
        shop_id = self.request.data.get('shop')
        if not user.is_admin:
            try:
                shop = Shop.objects.using('marketplace_db').get(id=shop_id, owner_id=user.id)
            except Shop.DoesNotExist:
                from rest_framework.exceptions import PermissionDenied
                raise PermissionDenied("Vous n'êtes pas propriétaire de cette boutique.")
        serializer.save()

    @action(detail=True, methods=['get', 'post'])
    def reviews(self, request, pk=None):
        product = self.get_object()
        if request.method == 'GET':
            reviews = ProductReview.objects.using('marketplace_db').filter(product=product)
            return Response(ProductReviewSerializer(reviews, many=True).data)

        if request.user.role not in ['CLIENT', 'ADMIN']:
            return Response({'error': 'Seuls les clients peuvent laisser des avis.'}, status=403)

        if ProductReview.objects.using('marketplace_db').filter(
            product=product, client_id=request.user.id
        ).exists():
            return Response({'error': 'Vous avez déjà laissé un avis sur ce produit.'}, status=400)

        serializer = ProductReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(product=product, client_id=request.user.id)
        return Response(serializer.data, status=201)

    @action(detail=False, methods=['get'])
    def featured(self, request):
        """Produits mis en avant"""
        products = Product.objects.using('marketplace_db').filter(
            is_featured=True, is_available=True
        )[:12]
        return Response(ProductSerializer(products, many=True).data)


class MarketplaceOrderViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['status', 'delivery_type']
    ordering = ['-created_at']

    def get_queryset(self):
        user = self.request.user
        qs = MarketplaceOrder.objects.using('marketplace_db').prefetch_related('order_items__product')

        if user.is_admin:
            return qs
        elif user.role == 'CLIENT':
            return qs.filter(client_id=user.id)
        elif user.role == 'LIVREUR':
            from django.db.models import Q
            return qs.filter(Q(livreur_id=user.id) | Q(status='READY', delivery_type='DELIVERY'))
        elif user.role == 'BOUTIQUIERR':
            owned_shops = Shop.objects.using('marketplace_db').filter(owner_id=user.id)
            return qs.filter(shop__in=owned_shops)
        return qs.none()

    def get_serializer_class(self):
        if self.action == 'create':
            return CreateMarketplaceOrderSerializer
        return MarketplaceOrderSerializer

    def create(self, request, *args, **kwargs):
        if request.user.role not in ['CLIENT', 'ADMIN']:
            return Response({'error': 'Seuls les clients peuvent passer des commandes.'}, status=403)
        serializer = CreateMarketplaceOrderSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        order = serializer.save()
        return Response(MarketplaceOrderSerializer(order).data, status=201)

    @action(detail=True, methods=['post'])
    def update_status(self, request, pk=None):
        """Mise à jour du statut selon le rôle"""
        order = self.get_object()
        new_status = request.data.get('status')
        user = request.user

        allowed = {
            'BOUTIQUIERR': {
                'PENDING': ['CONFIRMED', 'CANCELLED'],
                'CONFIRMED': ['PROCESSING'],
                'PROCESSING': ['READY', 'PICKUP_READY'],
                'LIVREUR_CANCELLED': ['READY'],  # Boutique confirme l'annulation du livreur
            },
            'LIVREUR': {
                'DELIVERING': ['DELIVERED'],
            },
            'CLIENT': {
                'PENDING': ['CANCELLED'],
            },
            'ADMIN': None,
        }

        role_allowed = allowed.get(user.role, {})
        if role_allowed is not None:
            if user.role == 'BOUTIQUIERR':
                shop = order.shop
                if shop.owner_id != user.id:
                    return Response({'error': 'Ce n\'est pas votre boutique.'}, status=403)
            ok = role_allowed.get(order.status, [])
            if new_status not in ok:
                return Response(
                    {'error': f"Transition '{order.status}' → '{new_status}' non autorisée."},
                    status=400
                )

        order.status = new_status
        if new_status == 'DELIVERED':
            order.delivered_at = timezone.now()
            order.shop.total_sales += 1
            order.shop.save(using='marketplace_db')
        elif new_status == 'READY' and user.role == 'BOUTIQUIERR':
            # Boutique confirme l'annulation du livreur → libérer la commande
            order.livreur_id = None
        order.save(using='marketplace_db')
        return Response(MarketplaceOrderSerializer(order).data)

    @action(detail=True, methods=['post'])
    def assign_livreur(self, request, pk=None):
        """
        Assigner un livreur pour la commande marketplace.
        Cross-service: livreur issu du service auth.
        """
        order = self.get_object()
        user = request.user

        if not user.is_admin:
            if user.role == 'BOUTIQUIERR' and order.shop.owner_id != user.id:
                return Response({'error': 'Permission refusée.'}, status=403)
            elif user.role == 'LIVREUR':
                if order.status != 'READY':
                    return Response({'error': 'La commande doit être prête pour être acceptée.'}, status=400)
                if order.livreur_id is not None:
                    return Response({'error': 'Un autre livreur a déjà accepté cette commande.'}, status=400)
                order.livreur_id = user.id
                order.status = MarketplaceOrder.Status.DELIVERING
                order.save(using='marketplace_db')
                return Response(MarketplaceOrderSerializer(order).data)
            else:
                return Response({'error': 'Permission refusée.'}, status=403)

        livreur_id = request.data.get('livreur_id')
        if not livreur_id:
            return Response({'error': 'livreur_id requis.'}, status=400)

        try:
            from apps.authentication.models import User
            User.objects.get(id=livreur_id, role='LIVREUR', is_active=True)
        except Exception:
            return Response({'error': 'Livreur introuvable.'}, status=404)

        order.livreur_id = livreur_id
        order.save(using='marketplace_db')
        return Response(MarketplaceOrderSerializer(order).data)

    @action(detail=True, methods=['post'])
    def cancel_delivery(self, request, pk=None):
        """Livreur annule la prise en charge — la boutique doit confirmer"""
        order = self.get_object()
        user = request.user

        if user.role != 'LIVREUR' and not user.is_admin:
            return Response({'error': 'Réservé aux livreurs.'}, status=403)

        if not user.is_admin and order.livreur_id != user.id:
            return Response({'error': 'Ce n\'est pas votre livraison.'}, status=403)

        if order.status != 'DELIVERING':
            return Response({'error': 'Impossible d\'annuler depuis cet état.'}, status=400)

        order.status = MarketplaceOrder.Status.LIVREUR_CANCELLED
        order.save(using='marketplace_db')
        return Response(MarketplaceOrderSerializer(order).data)

    @action(detail=False, methods=['get'])
    def available_for_delivery(self, request):
        """Commandes prêtes pour livraison - pour les livreurs"""
        if request.user.role not in ['LIVREUR', 'ADMIN']:
            return Response({'error': 'Réservé aux livreurs.'}, status=403)
        orders = MarketplaceOrder.objects.using('marketplace_db').filter(
            status='READY', delivery_type='DELIVERY', livreur_id=None
        )
        return Response(MarketplaceOrderSerializer(orders, many=True).data)


class AdminMarketplaceStatsView(generics.GenericAPIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        from django.db.models import Sum, Count
        orders = MarketplaceOrder.objects.using('marketplace_db')
        stats = {
            'total_orders': orders.count(),
            'pending': orders.filter(status='PENDING').count(),
            'delivered': orders.filter(status='DELIVERED').count(),
            'cancelled': orders.filter(status='CANCELLED').count(),
            'total_shops': Shop.objects.using('marketplace_db').count(),
            'active_shops': Shop.objects.using('marketplace_db').filter(is_active=True).count(),
            'total_products': Product.objects.using('marketplace_db').count(),
            'available_products': Product.objects.using('marketplace_db').filter(is_available=True).count(),
            'total_categories': Category.objects.using('marketplace_db').count(),
            'revenue': str(orders.filter(status='DELIVERED').aggregate(
                total=Sum('total_price'))['total'] or 0),
        }
        return Response(stats)
