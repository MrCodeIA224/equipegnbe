from rest_framework import viewsets, generics, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from django.utils import timezone

from .models import MarketRequest, MarketItem, CoursierOffer, MarketRating
from .serializers import (
    MarketRequestSerializer, CreateMarketRequestSerializer,
    MarketItemSerializer, CoursierOfferSerializer,
    UpdateMarketItemsSerializer, MarketRatingSerializer
)
from apps.authentication.permissions import IsAdmin, IsCoursierOrAdmin


class MarketRequestViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['status', 'market_name', 'delivery_city']
    search_fields = ['title', 'market_name', 'delivery_address']
    ordering = ['-created_at']

    def get_queryset(self):
        user = self.request.user
        qs = MarketRequest.objects.using('market_db').prefetch_related('items', 'offers')

        if user.is_admin:
            return qs
        elif user.role == 'CLIENT':
            return qs.filter(client_id=user.id)
        elif user.role == 'COURSIER':
            # Coursier voit ses missions + les demandes ouvertes
            from django.db.models import Q
            return qs.filter(Q(coursier_id=user.id) | Q(status='OPEN'))
        elif user.role == 'LIVREUR':
            # Livreur voit les demandes prêtes à être livrées + ses livraisons
            from django.db.models import Q
            return qs.filter(Q(livreur_id=user.id) | Q(status='NEED_DELIVERY'))
        return qs.none()

    def get_serializer_class(self):
        if self.action == 'create':
            return CreateMarketRequestSerializer
        return MarketRequestSerializer

    def create(self, request, *args, **kwargs):
        if request.user.role not in ['CLIENT', 'ADMIN']:
            return Response({'error': 'Seuls les clients peuvent créer des demandes.'}, status=403)
        serializer = CreateMarketRequestSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        market_request = serializer.save()
        return Response(MarketRequestSerializer(market_request).data, status=201)

    @action(detail=True, methods=['post'])
    def make_offer(self, request, pk=None):
        """Coursier propose de faire les courses"""
        if request.user.role not in ['COURSIER', 'ADMIN']:
            return Response({'error': 'Réservé aux coursiers.'}, status=403)

        market_request = self.get_object()
        if market_request.status != 'OPEN':
            return Response({'error': 'Cette demande n\'est plus disponible.'}, status=400)

        # Éviter les doublons
        if CoursierOffer.objects.using('market_db').filter(
            request=market_request, coursier_id=request.user.id
        ).exists():
            return Response({'error': 'Vous avez déjà soumis une offre.'}, status=400)

        offer = CoursierOffer.objects.using('market_db').create(
            request=market_request,
            coursier_id=request.user.id,
            message=request.data.get('message', ''),
            proposed_fee=request.data.get('proposed_fee', 0)
        )
        return Response(CoursierOfferSerializer(offer).data, status=201)

    @action(detail=True, methods=['post'])
    def accept_offer(self, request, pk=None):
        """Client accepte l'offre d'un coursier"""
        market_request = self.get_object()

        if market_request.client_id != request.user.id and not request.user.is_admin:
            return Response({'error': 'Permission refusée.'}, status=403)

        if market_request.status != 'OPEN':
            return Response({'error': 'Cette demande n\'est plus disponible.'}, status=400)

        offer_id = request.data.get('offer_id')
        try:
            offer = CoursierOffer.objects.using('market_db').get(id=offer_id, request=market_request)
        except CoursierOffer.DoesNotExist:
            return Response({'error': 'Offre introuvable.'}, status=404)

        offer.is_accepted = True
        offer.save(using='market_db')

        market_request.coursier_id = offer.coursier_id
        market_request.service_fee = offer.proposed_fee or market_request.service_fee
        market_request.status = 'ASSIGNED'
        market_request.save(using='market_db')

        return Response(MarketRequestSerializer(market_request).data)

    @action(detail=True, methods=['post'])
    def update_status(self, request, pk=None):
        """Mise à jour du statut selon le rôle"""
        market_request = self.get_object()
        new_status = request.data.get('status')
        user = request.user

        allowed = {
            'COURSIER': {
                'ASSIGNED': ['SHOPPING'],
                'SHOPPING': ['NEED_DELIVERY'],
            },
            'LIVREUR': {
                'NEED_DELIVERY': ['DELIVERING'],
                'DELIVERING': ['COMPLETED'],
            },
            'CLIENT': {
                'OPEN': ['CANCELLED'],
                'ASSIGNED': ['CANCELLED'],
            },
            'ADMIN': None,
        }

        role_allowed = allowed.get(user.role, {})
        if role_allowed is not None:
            ok = role_allowed.get(market_request.status, [])
            if new_status not in ok:
                return Response(
                    {'error': f"Transition '{market_request.status}' → '{new_status}' non autorisée."},
                    status=400
                )

        market_request.status = new_status
        if new_status == 'COMPLETED':
            market_request.completed_at = timezone.now()
        market_request.save(using='market_db')
        return Response(MarketRequestSerializer(market_request).data)

    @action(detail=True, methods=['post'])
    def assign_livreur(self, request, pk=None):
        """
        Assigner un livreur pour la livraison finale.
        Accessible par le coursier ou le client (ou admin).
        C'est le point de connexion entre le module Marché et les Livreurs.
        """
        market_request = self.get_object()

        if market_request.status != 'NEED_DELIVERY':
            return Response({'error': 'Les courses doivent être terminées avant d\'assigner un livreur.'}, status=400)

        if not request.user.is_admin:
            if market_request.client_id != request.user.id and market_request.coursier_id != request.user.id:
                return Response({'error': 'Permission refusée.'}, status=403)

        livreur_id = request.data.get('livreur_id')
        if not livreur_id:
            return Response({'error': 'livreur_id requis.'}, status=400)

        # Vérifier que le livreur existe et est disponible (cross-service)
        try:
            from apps.authentication.models import User
            livreur = User.objects.get(id=livreur_id, role='LIVREUR', is_active=True)
        except Exception:
            return Response({'error': 'Livreur introuvable ou non disponible.'}, status=404)

        market_request.livreur_id = livreur_id
        market_request.delivery_fee = request.data.get('delivery_fee', market_request.delivery_fee)
        market_request.save(using='market_db')

        return Response(MarketRequestSerializer(market_request).data)

    @action(detail=True, methods=['post'])
    def update_items(self, request, pk=None):
        """Coursier met à jour les articles (prix réels, disponibilité)"""
        market_request = self.get_object()

        if market_request.coursier_id != request.user.id and not request.user.is_admin:
            return Response({'error': 'Réservé au coursier assigné.'}, status=403)

        items_data = request.data.get('items', [])
        total_actual = 0

        for item_data in items_data:
            item_id = item_data.get('id')
            try:
                item = MarketItem.objects.using('market_db').get(id=item_id, request=market_request)
                item.actual_price = item_data.get('actual_price', item.actual_price)
                item.is_found = item_data.get('is_found', item.is_found)
                item.save(using='market_db')
                if item.actual_price:
                    total_actual += item.actual_price
            except MarketItem.DoesNotExist:
                pass

        market_request.actual_total = total_actual
        market_request.save(using='market_db')
        return Response(MarketRequestSerializer(market_request).data)

    @action(detail=False, methods=['get'])
    def open_requests(self, request):
        """Demandes ouvertes disponibles pour les coursiers"""
        if request.user.role not in ['COURSIER', 'ADMIN']:
            return Response({'error': 'Réservé aux coursiers.'}, status=403)
        requests = MarketRequest.objects.using('market_db').filter(status='OPEN')
        return Response(MarketRequestSerializer(requests, many=True).data)

    @action(detail=False, methods=['get'])
    def need_delivery(self, request):
        """Demandes prêtes à être livrées - pour les livreurs"""
        if request.user.role not in ['LIVREUR', 'ADMIN']:
            return Response({'error': 'Réservé aux livreurs.'}, status=403)
        requests = MarketRequest.objects.using('market_db').filter(
            status='NEED_DELIVERY', livreur_id=None
        )
        return Response(MarketRequestSerializer(requests, many=True).data)


class AdminMarketStatsView(generics.GenericAPIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        from django.db.models import Sum
        requests = MarketRequest.objects.using('market_db')
        stats = {
            'total_requests': requests.count(),
            'open': requests.filter(status='OPEN').count(),
            'in_progress': requests.filter(status__in=['ASSIGNED', 'SHOPPING', 'NEED_DELIVERY', 'DELIVERING']).count(),
            'completed': requests.filter(status='COMPLETED').count(),
            'cancelled': requests.filter(status='CANCELLED').count(),
            'revenue_service_fees': str(requests.filter(status='COMPLETED').aggregate(
                total=Sum('service_fee'))['total'] or 0),
        }
        return Response(stats)
