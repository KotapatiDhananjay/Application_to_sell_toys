from django.contrib import admin

from .models import Category, Product, ProductImage, StockAdjustment


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "is_active", "sort_order")
    list_editable = ("is_active", "sort_order")
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name",)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        "name", "category", "sku", "price", "discount_percent",
        "stock", "is_featured", "is_active",
    )
    list_editable = ("discount_percent", "stock", "is_featured", "is_active")
    list_filter = ("category", "is_featured", "is_active")
    search_fields = ("name", "sku", "brand")
    prepopulated_fields = {"slug": ("name",)}
    inlines = [ProductImageInline]


@admin.register(StockAdjustment)
class StockAdjustmentAdmin(admin.ModelAdmin):
    list_display = ("product", "change", "stock_after", "reason", "created_by", "created_at")
    list_filter = ("reason",)
    search_fields = ("product__name", "product__sku")
    readonly_fields = [f.name for f in StockAdjustment._meta.fields]

    def has_add_permission(self, request):
        return False  # ledger is append-only via Product.adjust_stock()

    def has_change_permission(self, request, obj=None):
        return False