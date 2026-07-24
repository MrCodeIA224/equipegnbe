from django.utils import timezone
from rest_framework import serializers
from .models import Category, Shop, Product, MarketplaceOrder, MarketplaceOrderItem, ProductReview, MarketplacePayment
from apps.authentication.services import validate_and_apply_promo, redeem_promo


class CategorySerializer(serializers.ModelSerializer):
    products_count = serializers.IntegerField(source='products.count', read_only=True)
    shops_count = serializers.IntegerField(source='shops.count', read_only=True)

    class Meta:
        model = Category
        fields = ['id', 'name', 'slug', 'description', 'icon', 'image',
                  'is_active', 'order', 'products_count', 'shops_count']


class ProductSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    shop_name = serializers.CharField(source='shop.name', read_only=True)
    condition_display = serializers.CharField(source='get_condition_display', read_only=True)

    class Meta:
        model = Product
        fields = [
            'id', 'name', 'description', 'price', 'stock', 'condition', 'condition_display',
            'image', 'image2', 'image3', 'is_available', 'is_featured', 'has_delivery',
            'views_count', 'category', 'category_name', 'shop', 'shop_name', 'created_at'
        ]
        read_only_fields = ['views_count', 'created_at']


class ShopSerializer(serializers.ModelSerializer):
    products = ProductSerializer(many=True, read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)
    owner_name = serializers.SerializerMethodField()
    products_count = serializers.IntegerField(source='products.count', read_only=True)

    class Meta:
        model = Shop
        fields = [
            'id', 'name', 'description', 'category', 'category_name',
            'address', 'city', 'latitude', 'longitude', 'phone', 'whatsapp', 'image', 'banner',
            'is_active', 'has_delivery', 'delivery_fee', 'rating', 'total_sales',
            'owner_id', 'owner_name', 'created_at', 'products', 'products_count'
        ]
        read_only_fields = ['rating', 'total_sales', 'created_at']

    def get_owner_name(self, obj):
        try:
            from apps.authentication.models import User
            user = User.objects.get(id=obj.owner_id)
            return user.get_full_name() or user.username
        except Exception:
            return f"Boutiquierr #{obj.owner_id}"


class ShopListSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    products_count = serializers.IntegerField(source='products.count', read_only=True)

    class Meta:
        model = Shop
        fields = [
            'id', 'name', 'description', 'category', 'category_name',
            'city', 'latitude', 'longitude', 'image', 'is_active', 'has_delivery',
            'delivery_fee', 'rating', 'total_sales', 'products_count'
        ]


class MarketplaceOrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_image = serializers.ImageField(source='product.image', read_only=True)
    subtotal = serializers.DecimalField(max_digits=12, decimal_places=0, read_only=True)

    class Meta:
        model = MarketplaceOrderItem
        fields = ['id', 'product', 'product_name', 'product_image', 'quantity', 'unit_price', 'subtotal']


class CreateOrderItemSerializer(serializers.Serializer):
    product_id = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1)


class PaymentSerializer(serializers.ModelSerializer):
    method_display = serializers.CharField(source='get_method_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = MarketplacePayment
        fields = [
            'method', 'method_display', 'status', 'status_display',
            'phone_number', 'transaction_reference', 'confirmed_at',
        ]


class CreateMarketplaceOrderSerializer(serializers.Serializer):
    shop_id = serializers.IntegerField()
    delivery_type = serializers.ChoiceField(choices=['DELIVERY', 'PICKUP'], default='DELIVERY')
    delivery_address = serializers.CharField(required=False, allow_blank=True)
    delivery_city = serializers.CharField(default='Conakry')
    notes = serializers.CharField(required=False, allow_blank=True)
    items = CreateOrderItemSerializer(many=True)
    payment_method = serializers.ChoiceField(
        choices=MarketplacePayment.Method.choices, default=MarketplacePayment.Method.CASH_ON_DELIVERY
    )
    phone_number = serializers.CharField(required=False, allow_blank=True)
    promo_code = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        if attrs.get('delivery_type') == 'DELIVERY' and not attrs.get('delivery_address'):
            raise serializers.ValidationError({'delivery_address': 'Adresse requise pour la livraison.'})
        if not attrs.get('items'):
            raise serializers.ValidationError({'items': 'La commande doit contenir au moins un article.'})
        if attrs['payment_method'] != MarketplacePayment.Method.CASH_ON_DELIVERY and not attrs.get('phone_number'):
            raise serializers.ValidationError({'phone_number': 'Numéro de téléphone requis pour ce mode de paiement.'})
        return attrs

    def create(self, validated_data):
        items_data = validated_data.pop('items')
        shop_id = validated_data.pop('shop_id')
        payment_method = validated_data.pop('payment_method')
        phone_number = validated_data.pop('phone_number', '')
        promo_code = validated_data.pop('promo_code', '')

        try:
            shop = Shop.objects.get(id=shop_id)
        except Shop.DoesNotExist:
            raise serializers.ValidationError({'shop_id': 'Boutique introuvable.'})

        if not shop.is_active:
            raise serializers.ValidationError({'shop_id': 'Cette boutique est inactive.'})

        request = self.context['request']
        delivery_fee = shop.delivery_fee if validated_data.get('delivery_type') == 'DELIVERY' else 0

        order = MarketplaceOrder.objects.using('marketplace_db').create(
            client_id=request.user.id,
            shop=shop,
            delivery_fee=delivery_fee,
            **validated_data
        )

        total = 0
        for item_data in items_data:
            try:
                product = Product.objects.get(id=item_data['product_id'], shop=shop, is_available=True)
            except Product.DoesNotExist:
                order.delete()
                raise serializers.ValidationError(
                    {'items': f"Produit {item_data['product_id']} introuvable dans cette boutique."}
                )

            if product.stock < item_data['quantity']:
                order.delete()
                raise serializers.ValidationError(
                    {'items': f"Stock insuffisant pour '{product.name}' (disponible: {product.stock})."}
                )

            MarketplaceOrderItem.objects.using('marketplace_db').create(
                order=order,
                product=product,
                quantity=item_data['quantity'],
                unit_price=product.price
            )
            total += product.price * item_data['quantity']
            # Décrémenter le stock
            product.stock -= item_data['quantity']
            product.save(using='marketplace_db')

        order.items_total = total
        discount_amount = 0
        promo = None
        if promo_code:
            result = validate_and_apply_promo(promo_code, request.user, 'MARKETPLACE', total)
            promo = result['promo']
            discount_amount = result['discount_amount']
            order.promo_code_used = promo.code
            order.discount_amount = discount_amount

        order.total_price = total + order.delivery_fee - discount_amount
        order.save(using='marketplace_db')

        if promo:
            redeem_promo(promo, request.user, 'MARKETPLACE', order.id, discount_amount)

        payment_status = (
            MarketplacePayment.Status.CONFIRMED if payment_method == MarketplacePayment.Method.CASH_ON_DELIVERY
            else MarketplacePayment.Status.PENDING
        )
        MarketplacePayment.objects.using('marketplace_db').create(
            order=order, method=payment_method, phone_number=phone_number,
            status=payment_status,
            confirmed_at=timezone.now() if payment_status == MarketplacePayment.Status.CONFIRMED else None,
        )

        return order


class MarketplaceOrderSerializer(serializers.ModelSerializer):
    order_items = MarketplaceOrderItemSerializer(many=True, read_only=True)
    shop_name = serializers.CharField(source='shop.name', read_only=True)
    shop_image = serializers.ImageField(source='shop.image', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    client_name = serializers.SerializerMethodField()
    livreur_name = serializers.SerializerMethodField()
    payment = PaymentSerializer(read_only=True)

    class Meta:
        model = MarketplaceOrder
        fields = [
            'id', 'client_id', 'client_name', 'livreur_id', 'livreur_name',
            'shop', 'shop_name', 'shop_image',
            'status', 'status_display', 'delivery_type',
            'delivery_address', 'delivery_city', 'notes',
            'items_total', 'delivery_fee', 'promo_code_used', 'discount_amount', 'total_price',
            'created_at', 'delivered_at', 'order_items', 'payment'
        ]
        read_only_fields = ['client_id', 'created_at']

    def get_client_name(self, obj):
        try:
            from apps.authentication.models import User
            return User.objects.get(id=obj.client_id).get_full_name()
        except Exception:
            return f"Client #{obj.client_id}"

    def get_livreur_name(self, obj):
        if not obj.livreur_id:
            return None
        try:
            from apps.authentication.models import User
            return User.objects.get(id=obj.livreur_id).get_full_name()
        except Exception:
            return f"Livreur #{obj.livreur_id}"


class ProductReviewSerializer(serializers.ModelSerializer):
    client_name = serializers.SerializerMethodField()

    class Meta:
        model = ProductReview
        fields = ['id', 'product', 'client_id', 'client_name', 'rating', 'comment', 'created_at']
        read_only_fields = ['client_id', 'created_at']

    def get_client_name(self, obj):
        try:
            from apps.authentication.models import User
            return User.objects.get(id=obj.client_id).get_full_name()
        except Exception:
            return f"Client #{obj.client_id}"
