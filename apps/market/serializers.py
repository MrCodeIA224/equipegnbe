from rest_framework import serializers
from .models import MarketRequest, MarketItem, CoursierOffer, MarketRating


class MarketItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = MarketItem
        fields = ['id', 'name', 'quantity', 'estimated_price', 'actual_price', 'is_found', 'notes']


class CoursierOfferSerializer(serializers.ModelSerializer):
    coursier_name = serializers.SerializerMethodField()

    class Meta:
        model = CoursierOffer
        fields = ['id', 'coursier_id', 'coursier_name', 'message', 'proposed_fee', 'is_accepted', 'created_at']
        read_only_fields = ['is_accepted', 'created_at']

    def get_coursier_name(self, obj):
        try:
            from apps.authentication.models import User
            user = User.objects.get(id=obj.coursier_id)
            return user.get_full_name() or user.username
        except Exception:
            return f"Coursier #{obj.coursier_id}"


class MarketRequestSerializer(serializers.ModelSerializer):
    items = MarketItemSerializer(many=True, read_only=True)
    offers = CoursierOfferSerializer(many=True, read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    client_name = serializers.SerializerMethodField()
    coursier_name = serializers.SerializerMethodField()
    livreur_name = serializers.SerializerMethodField()
    total_items = serializers.IntegerField(source='items.count', read_only=True)

    class Meta:
        model = MarketRequest
        fields = [
            'id', 'client_id', 'client_name', 'coursier_id', 'coursier_name',
            'livreur_id', 'livreur_name', 'status', 'status_display',
            'title', 'market_name', 'delivery_address', 'delivery_city',
            'budget', 'notes', 'is_delivery_needed',
            'service_fee', 'delivery_fee', 'actual_total',
            'created_at', 'completed_at',
            'items', 'offers', 'total_items'
        ]
        read_only_fields = ['client_id', 'status', 'actual_total', 'created_at']

    def get_client_name(self, obj):
        try:
            from apps.authentication.models import User
            user = User.objects.get(id=obj.client_id)
            return user.get_full_name() or user.username
        except Exception:
            return f"Client #{obj.client_id}"

    def get_coursier_name(self, obj):
        if not obj.coursier_id:
            return None
        try:
            from apps.authentication.models import User
            user = User.objects.get(id=obj.coursier_id)
            return user.get_full_name() or user.username
        except Exception:
            return f"Coursier #{obj.coursier_id}"

    def get_livreur_name(self, obj):
        if not obj.livreur_id:
            return None
        try:
            from apps.authentication.models import User
            user = User.objects.get(id=obj.livreur_id)
            return user.get_full_name() or user.username
        except Exception:
            return f"Livreur #{obj.livreur_id}"


class CreateMarketRequestSerializer(serializers.Serializer):
    title = serializers.CharField(default='Mes courses')
    market_name = serializers.CharField()
    delivery_address = serializers.CharField()
    delivery_city = serializers.CharField(default='Conakry')
    budget = serializers.DecimalField(max_digits=12, decimal_places=0, required=False, default=0)
    notes = serializers.CharField(required=False, allow_blank=True)
    is_delivery_needed = serializers.BooleanField(default=True)
    items = MarketItemSerializer(many=True)

    def validate_items(self, value):
        if not value:
            raise serializers.ValidationError('La liste de courses ne peut pas être vide.')
        return value

    def create(self, validated_data):
        items_data = validated_data.pop('items')
        request_obj = self.context['request']
        market_request = MarketRequest.objects.using('market_db').create(
            client_id=request_obj.user.id,
            **validated_data
        )
        for item_data in items_data:
            MarketItem.objects.using('market_db').create(request=market_request, **item_data)
        return market_request


class UpdateMarketItemsSerializer(serializers.Serializer):
    """Coursier met à jour les articles (prix réels, trouvé ou non)"""
    items = serializers.ListField(child=serializers.DictField())

    def validate_items(self, value):
        for item in value:
            if 'id' not in item:
                raise serializers.ValidationError('Chaque article doit avoir un id.')
        return value


class MarketRatingSerializer(serializers.ModelSerializer):
    class Meta:
        model = MarketRating
        fields = ['id', 'request', 'coursier_rating', 'livreur_rating', 'comment', 'created_at']
        read_only_fields = ['created_at']
