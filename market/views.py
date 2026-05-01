from rest_framework import viewsets, permissions, filters
from rest_framework.pagination import PageNumberPagination
from django_filters.rest_framework import DjangoFilterBackend
from accounts.permissions import IsFarmer, IsAdminRole, IsOwnerOrAdminRole
from .models import Category, Product
from .serializers import CategorySerializer, ProductSerializer
from .filters import ProductFilter
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.decorators import action
from rest_framework.response import Response


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
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    pagination_class = ProductPagination  # ← добавили
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter,
                       filters.SearchFilter]
    filterset_class = ProductFilter
    ordering_fields = ["price", "created_at"]
    ordering = ["-created_at"]
    search_fields = ["title", "description"]

    def get_queryset(self):
        # Добавляем защиту для Swagger
        if getattr(self, 'swagger_fake_view', False):
            return Product.objects.none()

        user = self.request.user
        # Проверяем, авторизован ли юзер, прежде чем смотреть его role
        if self.action in ["update", "partial_update", "destroy"]:
            if user.is_authenticated and hasattr(user, 'role') and user.role == "farmer":
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
    
    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def my(self, request):
        products = Product.objects.filter(owner=request.user).order_by('-created_at')
        page = self.paginate_queryset(products)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(products, many=True)
        return Response(serializer.data)

    def perform_create(self, serializer):
        print("DATA:", self.request.data)  # ← добавь
        print("FILES:", self.request.FILES)  # ← добавь
        serializer.save(owner=self.request.user)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            print("ERRORS:", serializer.errors)  # ← добавь
            return Response(serializer.errors, status=400)
        return super().create(request, *args, **kwargs)