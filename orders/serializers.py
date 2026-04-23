from rest_framework import serializers
from .models import Order, OrderItem, Review, Like
from market.models import Product


class OrderItemCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = ("product", "quantity")


class OrderItemSerializer(serializers.ModelSerializer):
    product_title = serializers.CharField(
        source="product.title", read_only=True
    )
    product_price = serializers.DecimalField(
        source="product.price",
        max_digits=10,
        decimal_places=2,
        read_only=True
    )
    subtotal = serializers.SerializerMethodField()

    class Meta:
        model = OrderItem
        fields = (
            "id", "product", "product_title",
            "product_price", "quantity",
            "price_at_order", "subtotal"
        )

    def get_subtotal(self, obj):
        return obj.subtotal()


class OrderCreateSerializer(serializers.ModelSerializer):
    items = OrderItemCreateSerializer(many=True)

    class Meta:
        model = Order
        fields = (
            "id",
            "delivery_name",      # ← Имя получателя
            "delivery_phone",     # ← Телефон
            "delivery_address",   # ← Улица, дом
            "delivery_city",      # ← Город
            "delivery_lat",       # ← Координаты (опционально)
            "delivery_lon",
            "comment",
            "items",
        )

    def validate_delivery_phone(self, value):
        # Убираем всё кроме цифр и +
        cleaned = ''.join(c for c in value if c.isdigit() or c == '+')
        if len(cleaned) < 9:
            raise serializers.ValidationError(
                "Введите корректный номер телефона"
            )
        return value

    def validate_items(self, items):
        if not items:
            raise serializers.ValidationError(
                "Заказ должен содержать хотя бы один товар"
            )
        return items

    def create(self, validated_data):
        items_data = validated_data.pop("items")
        customer = self.context["request"].user

        order = Order.objects.create(
            customer=customer,
            **validated_data
        )

        for item_data in items_data:
            product = item_data["product"]
            OrderItem.objects.create(
                order=order,
                product=product,
                quantity=item_data["quantity"],
                price_at_order=product.price,
            )

        order.calculate_total()
        return order


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    customer_email = serializers.EmailField(
        source="customer.email", read_only=True
    )
    status_display = serializers.CharField(
        source="get_status_display", read_only=True
    )

    class Meta:
        model = Order
        fields = (
            "id",
            "customer_email",
            "status",
            "status_display",
            "delivery_name",
            "delivery_phone",
            "delivery_address",
            "delivery_city",
            "delivery_lat",
            "delivery_lon",
            "total_price",
            "comment",
            "created_at",
            "items",
        )
        read_only_fields = (
            "id", "customer_email",
            "total_price", "created_at",
            "status_display", "items"
        )


class ReviewSerializer(serializers.ModelSerializer):
    author_email = serializers.EmailField(
        source="author.email", read_only=True
    )

    class Meta:
        model = Review
        fields = (
            "id", "product", "author_email",
            "rating", "text", "created_at"
        )
        read_only_fields = (
            "id", "author_email", "created_at", "product"
        )


class LikeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Like
        fields = ("id", "product", "created_at")
        read_only_fields = ("id", "created_at")