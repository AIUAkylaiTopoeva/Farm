import django_filters
from django.db.models import Q
from .models import Product

class ProductFilter(django_filters.FilterSet):
    min_price = django_filters.NumberFilter(field_name="price", lookup_expr="gte")
    max_price = django_filters.NumberFilter(field_name="price", lookup_expr="lte")

    # фильтр по slug категории (удобно для UI)
    category = django_filters.CharFilter(field_name="category__slug", lookup_expr="iexact")

    # поиск по title/description
    q = django_filters.CharFilter(method="filter_q")

    def filter_q(self, queryset, name, value):
        return queryset.filter(Q(title__icontains=value) | Q(description__icontains=value))

    class Meta:
        model = Product
        fields = ["is_active", "category", "min_price", "max_price", "q"]