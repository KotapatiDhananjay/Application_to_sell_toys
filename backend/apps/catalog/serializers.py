from rest_framework import serializers

from apps.core.utils import absolute_url

from .models import Category, Product, ProductImage


class CategorySerializer(serializers.ModelSerializer):
    product_count = serializers.IntegerField(read_only=True)
    image = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ("id", "name", "slug", "description", "image", "product_count")

    def get_image(self, obj):
        request = self.context.get("request")
        return absolute_url(request, obj.image.url if obj.image else obj.image_url) or None


class CategoryBriefSerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ("id", "name", "slug")


class ProductImageSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()

    class Meta:
        model = ProductImage
        fields = ("id", "url", "alt_text", "is_primary")

    def get_url(self, obj):
        return absolute_url(self.context.get("request"), obj.url)


class ProductListSerializer(serializers.ModelSerializer):
    """Compact product data for cards / grids."""

    category = CategoryBriefSerializer(read_only=True)
    discounted_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    has_discount = serializers.BooleanField(read_only=True)
    in_stock = serializers.BooleanField(read_only=True)
    stock_status = serializers.CharField(read_only=True)  # in_stock | low_stock | out_of_stock
    age_range = serializers.CharField(source="age_range_label", read_only=True)
    image = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = (
            "id", "name", "slug", "sku", "brand", "short_description", "category",
            "price", "discount_percent", "discounted_price", "has_discount",
            "stock", "in_stock", "stock_status",
            "age_min", "age_max", "age_range", "is_featured", "image", "created_at",
        )

    def get_image(self, obj):
        # Uses the prefetched images (already ordered primary-first): no extra query.
        images = list(obj.images.all())
        if not images:
            return None
        return absolute_url(self.context.get("request"), images[0].url) or None


class ProductDetailSerializer(ProductListSerializer):
    """Everything needed for the product page."""

    images = ProductImageSerializer(many=True, read_only=True)
    related_products = serializers.SerializerMethodField()

    class Meta(ProductListSerializer.Meta):
        fields = ProductListSerializer.Meta.fields + (
            "description", "low_stock_threshold", "images", "related_products",
        )

    def get_related_products(self, obj):
        related = (
            Product.objects.filter(is_active=True, category=obj.category)
            .exclude(pk=obj.pk)
            .select_related("category")
            .prefetch_related("images")
            .order_by("-is_featured", "-created_at")[:4]
        )
        return ProductListSerializer(related, many=True, context=self.context).data