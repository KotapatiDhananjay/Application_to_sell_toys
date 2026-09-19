from django.db.models import Count, DecimalField, ExpressionWrapper, F, Q, Value
from django.db.models.functions import Round
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.permissions import AllowAny

from apps.core.filters import StableOrderingFilter

from .filters import ProductFilter
from .models import Category, Product
from .serializers import CategorySerializer, ProductDetailSerializer, ProductListSerializer

# Price after discount, computed in the database so we can filter and sort on it.
# Mirrors Product.discounted_price (price x (100 - discount%) / 100, 2 decimals).
FINAL_PRICE = Round(
    ExpressionWrapper(
        F("price") * (100 - F("discount_percent")) / Value(100),
        output_field=DecimalField(max_digits=14, decimal_places=4),
    ),
    2,
)


def public_products():
    """Products a shopper may see: active product in an active category."""
    return (
        Product.objects.filter(is_active=True, category__is_active=True)
        .select_related("category")
        .prefetch_related("images")
        .annotate(final_price=FINAL_PRICE)
    )


class CategoryListView(ListAPIView):
    """GET /api/categories/"""

    serializer_class = CategorySerializer
    permission_classes = [AllowAny]
    pagination_class = None

    def get_queryset(self):
        return Category.objects.filter(is_active=True).annotate(
            product_count=Count("products", filter=Q(products__is_active=True))
        )


class ProductListView(ListAPIView):
    """GET /api/products/  - search, filter, sort and paginate.

    ?search=robot   ?category=dolls   ?min_price=10&max_price=50   ?age=5
    ?in_stock=true  ?on_sale=true     ?featured=true
    ?ordering=final_price | -final_price | -created_at | name | -discount_percent
    ?page=2&page_size=12
    """

    serializer_class = ProductListSerializer
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend, SearchFilter, StableOrderingFilter]
    filterset_class = ProductFilter
    search_fields = ["name", "brand", "short_description", "description", "category__name"]
    ordering_fields = ["final_price", "created_at", "name", "discount_percent"]
    ordering = ["-created_at"]

    def get_queryset(self):
        return public_products()


class ProductDetailView(RetrieveAPIView):
    """GET /api/products/<slug>/"""

    serializer_class = ProductDetailSerializer
    permission_classes = [AllowAny]
    lookup_field = "slug"

    def get_queryset(self):
        return public_products()