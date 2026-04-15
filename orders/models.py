from django.db import models
from django.conf import settings
from market.models import Product


class Order(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Ожидает"
        CONFIRMED = "confirmed", "Подтверждён"
        DELIVERING = "delivering", "В доставке"
        DONE = "done", "Выполнен"
        CANCELLED = "cancelled", "Отменён"

    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="orders"
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )
    # Адрес доставки — подробный
    delivery_address = models.CharField(
        max_length=255,
        help_text="Улица, дом, квартира"
    )
    delivery_city = models.CharField(
        max_length=100,
        default="Бишкек"
    )
    delivery_lat = models.FloatField(
        null=True, blank=True,
        help_text="Широта точки доставки"
    )
    delivery_lon = models.FloatField(
        null=True, blank=True,
        help_text="Долгота точки доставки"
    )
    delivery_phone = models.CharField(
        max_length=20,
        help_text="Телефон для связи"
    )
    delivery_name = models.CharField(
        max_length=100,
        help_text="Имя получателя"
    )

    total_price = models.DecimalField(
        max_digits=10, decimal_places=2, default=0
    )
    comment = models.TextField(
        blank=True, default="",
        help_text="Комментарий к заказу"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def calculate_total(self):
        total = sum(
            item.quantity * item.price_at_order
            for item in self.items.all()
        )
        self.total_price = total
        self.save(update_fields=["total_price"])


class OrderItem(models.Model):
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="items"
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name="order_items"
    )
    quantity = models.PositiveIntegerField(default=1)
    price_at_order = models.DecimalField(
        max_digits=10, decimal_places=2
    )

    def __str__(self):
        return f"{self.product.title} x{self.quantity}"

    def subtotal(self):
        return self.quantity * self.price_at_order


class Review(models.Model):
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="reviews"
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="reviews"
    )
    rating = models.PositiveSmallIntegerField(
        default=5,
        choices=[(i, i) for i in range(1, 6)]
    )
    text = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        unique_together = ("product", "author")

    def __str__(self):
        return f"Review by {self.author.email} on {self.product.title}"


class Like(models.Model):
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="likes"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="likes"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("product", "user")

    def __str__(self):
        return f"{self.user.email} liked {self.product.title}"