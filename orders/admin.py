from django.contrib import admin
from .models import Order, OrderItem, Review, Like


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ("product", "quantity", "price_at_order", "subtotal")

    def subtotal(self, obj):
        return obj.subtotal()
    subtotal.short_description = "Сумма"


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        "id", "customer", "status", "total_price",
        "delivery_city", "delivery_name", "created_at"
    )
    list_filter = ("status", "delivery_city", "created_at")
    search_fields = (
        "customer__email", "delivery_name",
        "delivery_phone", "delivery_address"
    )
    readonly_fields = ("total_price", "created_at", "updated_at")
    ordering = ("-created_at",)
    inlines = [OrderItemInline]

    fieldsets = (
        ("Заказ", {
            "fields": ("customer", "status", "total_price", "comment")
        }),
        ("Доставка", {
            "fields": (
                "delivery_name", "delivery_phone",
                "delivery_address", "delivery_city",
                "delivery_lat", "delivery_lon",
            )
        }),
        ("Даты", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",),
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("customer")


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ("id", "order", "product", "quantity", "price_at_order")
    search_fields = ("product__title", "order__customer__email")
    readonly_fields = ("price_at_order",)

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("order", "product")


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ("id", "product", "author", "rating", "created_at")
    list_filter = ("rating", "created_at")
    search_fields = ("product__title", "author__email", "text")
    readonly_fields = ("created_at",)

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("product", "author")


@admin.register(Like)
class LikeAdmin(admin.ModelAdmin):
    list_display = ("id", "product", "user", "created_at")
    search_fields = ("product__title", "user__email")
    readonly_fields = ("created_at",)

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("product", "user")