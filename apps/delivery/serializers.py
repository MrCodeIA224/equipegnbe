from django.utils import timezone
from rest_framework import serializers
from .models import Restaurant, MenuItem, FoodCategory, DeliveryOrder, DeliveryOrderItem, DeliveryRating, DeliveryPayment
from apps.authentication.services import validate_and_apply_promo, redeem_promo


class FoodCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = FoodCategory
        fields = ['id', 'name', 'icon']


class MenuItemSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)

    class Meta:
        model = MenuItem
        fields = ['id', 'name', 'description', 'price', 'image',
                  'is_available', 'is_popular', 'category', 'category_name']


class RestaurantSerializer(serializers.ModelSerializer):
    menu_items = MenuItemSerializer(many=True, read_only=True)
    delivery_time = serializers.CharField(read_only=True)
    owner_name = serializers.SerializerMethodField()

    class Meta:
        model = Restaurant
        fields = [
            'id', 'name', 'description', 'address', 'city', 'phone',
            'image', 'banner', 'is_open', 'delivery_time', 'delivery_time_min',
            'delivery_time_max', 'min_order', 'delivery_fee', 'rating',
            'total_orders', 'owner_id', 'owner_name', 'created_at', 'menu_items'
        ]
        read_only_fields = ['rating', 'total_orders', 'created_at']

    def get_owner_name(self, obj):
        # Cross-service: récupérer le nom du propriétaire depuis auth
        try:
            from apps.authentication.models import User
            user = User.objects.get(id=obj.owner_id)
            return user.get_full_name() or user.username
        except Exception:
            return f"Propriétaire #{obj.owner_id}"


class RestaurantListSerializer(serializers.ModelSerializer):
    """Version allégée pour les listes"""
    delivery_time = serializers.CharField(read_only=True)

    class Meta:
        model = Restaurant
        fields = [
            'id', 'name', 'description', 'address', 'city',
            'image', 'is_open', 'delivery_time', 'min_order',
            'delivery_fee', 'rating', 'total_orders'
        ]


class DeliveryOrderItemSerializer(serializers.ModelSerializer):
    menu_item_name = serializers.CharField(source='menu_item.name', read_only=True)
    subtotal = serializers.DecimalField(max_digits=12, decimal_places=0, read_only=True)

    class Meta:
        model = DeliveryOrderItem
        fields = ['id', 'menu_item', 'menu_item_name', 'quantity', 'unit_price', 'subtotal', 'notes']


class CreateOrderItemSerializer(serializers.Serializer):
    menu_item_id = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1)
    notes = serializers.CharField(required=False, allow_blank=True)


class PaymentSerializer(serializers.ModelSerializer):
    method_display = serializers.CharField(source='get_method_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = DeliveryPayment
        fields = [
            'method', 'method_display', 'status', 'status_display',
            'phone_number', 'transaction_reference', 'confirmed_at',
        ]


class CreateDeliveryOrderSerializer(serializers.Serializer):
    restaurant_id = serializers.IntegerField()
    delivery_address = serializers.CharField()
    delivery_city = serializers.CharField(default='Conakry')
    notes = serializers.CharField(required=False, allow_blank=True)
    items = CreateOrderItemSerializer(many=True)
    payment_method = serializers.ChoiceField(
        choices=DeliveryPayment.Method.choices, default=DeliveryPayment.Method.CASH_ON_DELIVERY
    )
    phone_number = serializers.CharField(required=False, allow_blank=True)
    promo_code = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        if not attrs.get('items'):
            raise serializers.ValidationError({'items': 'La commande doit contenir au moins un article.'})
        if attrs['payment_method'] != DeliveryPayment.Method.CASH_ON_DELIVERY and not attrs.get('phone_number'):
            raise serializers.ValidationError({'phone_number': 'Numéro de téléphone requis pour ce mode de paiement.'})
        return attrs

    def create(self, validated_data):
        items_data = validated_data.pop('items')
        restaurant_id = validated_data.pop('restaurant_id')
        payment_method = validated_data.pop('payment_method')
        phone_number = validated_data.pop('phone_number', '')
        promo_code = validated_data.pop('promo_code', '')

        try:
            restaurant = Restaurant.objects.get(id=restaurant_id)
        except Restaurant.DoesNotExist:
            raise serializers.ValidationError({'restaurant_id': 'Restaurant introuvable.'})

        if not restaurant.is_open:
            raise serializers.ValidationError({'restaurant_id': 'Ce restaurant est actuellement fermé.'})

        request = self.context['request']
        order = DeliveryOrder.objects.using('delivery_db').create(
            client_id=request.user.id,
            restaurant=restaurant,
            delivery_fee=restaurant.delivery_fee,
            **validated_data
        )

        total = 0
        for item_data in items_data:
            try:
                menu_item = MenuItem.objects.get(id=item_data['menu_item_id'], restaurant=restaurant)
            except MenuItem.DoesNotExist:
                order.delete()
                raise serializers.ValidationError(
                    {'items': f"Article {item_data['menu_item_id']} introuvable dans ce restaurant."}
                )
            unit_price = menu_item.price
            DeliveryOrderItem.objects.using('delivery_db').create(
                order=order,
                menu_item=menu_item,
                quantity=item_data['quantity'],
                unit_price=unit_price,
                notes=item_data.get('notes', '')
            )
            total += unit_price * item_data['quantity']

        order.items_total = total
        discount_amount = 0
        promo = None
        if promo_code:
            result = validate_and_apply_promo(promo_code, request.user, 'DELIVERY', total)
            promo = result['promo']
            discount_amount = result['discount_amount']
            order.promo_code_used = promo.code
            order.discount_amount = discount_amount

        order.total_price = total + order.delivery_fee - discount_amount
        order.save(using='delivery_db')

        if promo:
            redeem_promo(promo, request.user, 'DELIVERY', order.id, discount_amount)

        payment_status = (
            DeliveryPayment.Status.CONFIRMED if payment_method == DeliveryPayment.Method.CASH_ON_DELIVERY
            else DeliveryPayment.Status.PENDING
        )
        DeliveryPayment.objects.using('delivery_db').create(
            order=order, method=payment_method, phone_number=phone_number,
            status=payment_status,
            confirmed_at=timezone.now() if payment_status == DeliveryPayment.Status.CONFIRMED else None,
        )

        return order


class DeliveryOrderSerializer(serializers.ModelSerializer):
    order_items = DeliveryOrderItemSerializer(many=True, read_only=True)
    restaurant_name = serializers.CharField(source='restaurant.name', read_only=True)
    restaurant_image = serializers.ImageField(source='restaurant.image', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    client_name = serializers.SerializerMethodField()
    livreur_name = serializers.SerializerMethodField()
    payment = PaymentSerializer(read_only=True)

    class Meta:
        model = DeliveryOrder
        fields = [
            'id', 'client_id', 'client_name', 'livreur_id', 'livreur_name',
            'restaurant', 'restaurant_name', 'restaurant_image',
            'status', 'status_display', 'delivery_address', 'delivery_city',
            'notes', 'items_total', 'delivery_fee', 'promo_code_used', 'discount_amount',
            'total_price', 'created_at', 'confirmed_at', 'picked_up_at', 'delivered_at',
            'order_items', 'payment'
        ]
        read_only_fields = ['client_id', 'created_at']

    def get_client_name(self, obj):
        try:
            from apps.authentication.models import User
            user = User.objects.get(id=obj.client_id)
            return user.get_full_name() or user.username
        except Exception:
            return f"Client #{obj.client_id}"

    def get_livreur_name(self, obj):
        if not obj.livreur_id:
            return None
        try:
            from apps.authentication.models import User
            user = User.objects.get(id=obj.livreur_id)
            return user.get_full_name() or user.username
        except Exception:
            return f"Livreur #{obj.livreur_id}"


class DeliveryRatingSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeliveryRating
        fields = ['id', 'order', 'restaurant_rating', 'livreur_rating', 'comment', 'created_at']
        read_only_fields = ['created_at']
