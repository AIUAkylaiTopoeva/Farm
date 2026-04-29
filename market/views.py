from rest_framework import viewsets, permissions, filters
from rest_framework.pagination import PageNumberPagination
from django_filters.rest_framework import DjangoFilterBackend
from accounts.permissions import IsFarmer, IsAdminRole, IsOwnerOrAdminRole
from .models import Category, Product
from .serializers import CategorySerializer, ProductSerializer
from .filters import ProductFilter
from rest_framework.parsers import MultiPartParser, FormParser


class ProductPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    lookup_field = "slug"

    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated(), IsAdminRole()]


class ProductViewSet(viewsets.ModelViewSet):
    serializer_class = ProductSerializer
    parser_classes = [MultiPartParser, FormParser]
    pagination_class = ProductPagination  # ← добавили
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter,
                       filters.SearchFilter]
    filterset_class = ProductFilter
    ordering_fields = ["price", "created_at"]
    ordering = ["-created_at"]
    search_fields = ["title", "description"]

    def get_queryset(self):
        user = self.request.user
        if self.action in ["update", "partial_update", "destroy"]:
            if user.is_authenticated and user.role == "farmer":
                return Product.objects.filter(owner=user)
        return Product.objects.select_related(
            "category", "owner").filter(is_active=True)

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