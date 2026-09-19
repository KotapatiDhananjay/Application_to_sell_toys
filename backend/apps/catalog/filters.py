from django.db.models import Q
from django_filters import rest_framework as filters

from .models import Product


class ProductFilter(filters.FilterSet):
    """Query-string filters for GET /api/products/

    ?category=dolls          category slug
    ?min_price=10&max_price=40   range on the price customers actually pay
    ?age=5                   toys suitable for a 5-year-old
    ?in_stock=true           only toys that are available
    ?on_sale=true            only discounted toys
    ?featured=true           only featured toys
    """

    category = filters.CharFilter(field_name="category__slug")
    min_price = filters.NumberFilter(field_name="final_price", lookup_expr="gte")
    max_price = filters.NumberFilter(field_name="final_price", lookup_expr="lte")
    age = filters.NumberFilter(method="filter_age")
    in_stock = filters.BooleanFilter(method="filter_in_stock")
    on_sale = filters.BooleanFilter(method="filter_on_sale")
    featured = filters.BooleanFilter(method="filter_featured")

    class Meta:
        model = Product
        fields = []

    def filter_age(self, queryset, name, value):
        # min age <= child's age, and (no max age OR max age >= child's age)
        return queryset.filter(age_min__lte=value).filter(
            Q(age_max__isnull=True) | Q(age_max__gte=value)
        )

    # The three switches below only act on "true"; "false" means "don't filter".
    def filter_in_stock(self, queryset, name, value):
        return queryset.filter(stock__gt=0) if value else queryset

    def filter_on_sale(self, queryset, name, value):
        return queryset.filter(discount_percent__gt=0) if value else queryset

    def filter_featured(self, queryset, name, value):
        return queryset.filter(is_featured=True) if value else queryset