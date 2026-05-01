from rest_framework import generics, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from django.shortcuts import get_object_or_404

from .models import Order, Review, Like
from .serializers import (
    OrderCreateSerializer,
    OrderSerializer,
    ReviewSerializer,
    LikeSerializer,
)
from market.models import Product
from market.serializers import ProductSerializer
from accounts.permissions import IsCustomer, IsFarmer

class OrderCreateView(generics.CreateAPIView):
    """POST /api/orders/ — создать заказ"""
    serializer_class = OrderCreateSerializer
    permission_classes = [permissions.IsAuthenticated, IsCustomer]

class OrderListView(generics.ListAPIView):
    """GET /api/orders/ — мои заказы"""
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Order.objects.none()
        
        user = self.request.user
        if user.role == "farmer":
            return Order.objects.filter(
                items__product__owner=user
            ).distinct().prefetch_related("items__product")
        return Order.objects.filter(
            customer=user
        ).prefetch_related("items__product")

class OrderDetailView(generics.RetrieveAPIView):
    """GET /api/orders/<id>/"""
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Order.objects.none()
            
        user = self.request.user
        if user.role == "farmer":
            return Order.objects.filter(
                items__product__owner=user
            ).distinct()
        return Order.objects.filter(customer=user)

class OrderStatusUpdateView(APIView):
    """PATCH /api/orders/<id>/status/ — фермер меняет статус"""
    permission_classes = [permissions.IsAuthenticated, IsFarmer]

    def patch(self, request, pk):
        order = get_object_or_404(
            Order,
            pk=pk,
            items__product__owner=request.user
        )
        new_status = request.data.get("status")
        allowed = ["confirmed", "delivering", "done", "cancelled"]
        if new_status not in allowed:
            return Response(
                {"error": f"Статус должен быть одним из: {allowed}"},
                status=status.HTTP_400_BAD_REQUEST
            )
        order.status = new_status
        order.save(update_fields=["status"])
        return Response(OrderSerializer(order).data)

class ReviewListCreateView(generics.ListCreateAPIView):
    serializer_class = ReviewSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        # ЗДЕСЬ НУЖНО ДОБАВИТЬ:
        if getattr(self, 'swagger_fake_view', False):
            return Review.objects.none()
            
        return Review.objects.filter(
            product_id=self.kwargs["product_id"]
        ).select_related("author")

    def perform_create(self, serializer):
        product = get_object_or_404(Product, pk=self.kwargs["product_id"])
        if product.owner == self.request.user:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Нельзя оставить отзыв на свой товар")
        serializer.save(author=self.request.user, product=product)

class ReviewDeleteView(generics.DestroyAPIView):
    serializer_class = ReviewSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Review.objects.none()
        return Review.objects.filter(author=self.request.user)

class LikeToggleView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, product_id):
        product = get_object_or_404(Product, pk=product_id)
        like, created = Like.objects.get_or_create(
            product=product,
            user=request.user
        )
        if not created:
            like.delete()
            return Response({"liked": False, "likes_count": product.likes.count()})
        return Response({"liked": True, "likes_count": product.likes.count()})

class ProductLikesView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, product_id):
        product = get_object_or_404(Product, pk=product_id)
        is_liked = False
        if request.user.is_authenticated:
            is_liked = Like.objects.filter(
                product=product,
                user=request.user
            ).exists()
        return Response({
            "likes_count": product.likes.count(),
            "is_liked": is_liked
        })

class AdminOrderListView(generics.ListAPIView):
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Order.objects.none()

        user = self.request.user
        if user.role == 'admin' or user.is_staff:
            return Order.objects.all().prefetch_related(
                'items__product').order_by('-created_at')
        return Order.objects.none()

class ReviewUpdateView(generics.UpdateAPIView):
    serializer_class = ReviewSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ['patch']

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Review.objects.none()
        return Review.objects.filter(author=self.request.user)

class LikedProductsView(generics.ListAPIView):
    serializer_class = ProductSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Product.objects.none()

        liked_ids = Like.objects.filter(
            user=self.request.user
        ).values_list('product_id', flat=True)
        return Product.objects.filter(id__in=liked_ids, is_active=True)