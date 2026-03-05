from rest_framework import viewsets, permissions, filters
from django_filters.rest_framework import DjangoFilterBackend

from accounts.permissions import IsFarmer, IsAdminRole
from .models import Category, Product
from .serializers import CategorySerializer, ProductSerializer
from .permissions import IsOwnerOrAdminRole
from .filters import ProductFilter

class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    lookup_field = "slug"

    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated(), IsAdminRole()]


class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.select_related("category", "owner").all()
    serializer_class = ProductSerializer

    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_class = ProductFilter

    ordering_fields = ["price", "created_at"]
    ordering = ["-created_at"]

    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            return [permissions.AllowAny()]
        if self.action == "create":
            return [permissions.IsAuthenticated(), IsFarmer()]
        if self.action in ["update", "partial_update", "destroy"]:
            return [permissions.IsAuthenticated(), IsOwnerOrAdminRole()]
        return [permissions.IsAuthenticated()]

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)