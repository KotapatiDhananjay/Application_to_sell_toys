from decimal import ROUND_HALF_UP, Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models, transaction
from django.utils.text import slugify

from apps.core.models import TimeStampedModel

from .exceptions import InsufficientStockError


def _unique_slug(model, value, instance_pk=None, max_length=170):
    """Build a slug from `value` that is unique for `model`."""
    base = slugify(value)[: max_length - 6] or "item"
    slug, n = base, 2
    qs = model.objects.exclude(pk=instance_pk)
    while qs.filter(slug=slug).exists():
        slug = f"{base}-{n}"
        n += 1
    return slug


class Category(TimeStampedModel):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=110, unique=True, blank=True)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to="categories/", blank=True)
    image_url = models.URLField(blank=True, help_text="Optional external image.")
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "name"]
        verbose_name_plural = "categories"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = _unique_slug(Category, self.name, self.pk, 110)
        super().save(*args, **kwargs)


class Product(TimeStampedModel):
    category = models.ForeignKey(
        Category, on_delete=models.PROTECT, related_name="products"
    )
    name = models.CharField(max_length=180)
    slug = models.SlugField(max_length=190, unique=True, blank=True)
    sku = models.CharField("SKU", max_length=40, unique=True)
    brand = models.CharField(max_length=80, blank=True)
    short_description = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)

    price = models.DecimalField(
        max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))]
    )
    discount_percent = models.PositiveSmallIntegerField(
        default=0,
        validators=[MaxValueValidator(90)],
        help_text="Percentage off the list price (0-90).",
    )
    stock = models.PositiveIntegerField(default=0)
    low_stock_threshold = models.PositiveIntegerField(default=5)

    age_min = models.PositiveSmallIntegerField(
        default=0, validators=[MaxValueValidator(18)], help_text="Recommended min age (years)."
    )
    age_max = models.PositiveSmallIntegerField(
        null=True, blank=True, validators=[MaxValueValidator(99)],
        help_text="Recommended max age (years). Leave empty for 'and up'.",
    )

    is_featured = models.BooleanField(default=False, db_index=True)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["is_active", "category"]),
            models.Index(fields=["price"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(price__gt=0), name="product_price_positive"
            ),
            models.CheckConstraint(
                condition=models.Q(discount_percent__lte=90),
                name="product_discount_max_90",
            ),
            models.CheckConstraint(
                condition=models.Q(age_max__isnull=True)
                | models.Q(age_max__gte=models.F("age_min")),
                name="product_age_range_valid",
            ),
        ]

    def __str__(self):
        return self.name

    # ------------------------------------------------------------ pricing
    @property
    def has_discount(self) -> bool:
        return self.discount_percent > 0

    @property
    def discounted_price(self) -> Decimal:
        """Selling price after discount, rounded to 2 decimals."""
        factor = Decimal(100 - self.discount_percent) / Decimal(100)
        return (self.price * factor).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    @property
    def savings(self) -> Decimal:
        return self.price - self.discounted_price

    # ---------------------------------------------------------- inventory
    @property
    def in_stock(self) -> bool:
        return self.stock > 0

    @property
    def is_low_stock(self) -> bool:
        return 0 < self.stock <= self.low_stock_threshold

    @property
    def stock_status(self) -> str:
        if not self.in_stock:
            return "out_of_stock"
        return "low_stock" if self.is_low_stock else "in_stock"

    @property
    def age_range_label(self) -> str:
        if self.age_max is None:
            return f"{self.age_min}+ years"
        if self.age_min == self.age_max:
            return f"{self.age_min} years"
        return f"{self.age_min}-{self.age_max} years"

    @property
    def primary_image_url(self) -> str:
        img = self.images.filter(is_primary=True).first() or self.images.first()
        return img.url if img else ""

    def clean(self):
        if self.age_max is not None and self.age_max < self.age_min:
            raise ValidationError({"age_max": "Max age cannot be lower than min age."})

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = _unique_slug(Product, self.name, self.pk, 190)
        super().save(*args, **kwargs)

    @transaction.atomic
    def adjust_stock(self, delta: int, reason: str, user=None, note: str = "") -> int:
        """Change stock by `delta` safely and record it in the audit log.

        Uses a row lock so two simultaneous checkouts cannot oversell the
        last unit. Raises `InsufficientStockError` if stock would go < 0.
        """
        locked = Product.objects.select_for_update().get(pk=self.pk)
        new_stock = locked.stock + delta
        if new_stock < 0:
            raise InsufficientStockError(self, delta, locked.stock)
        locked.stock = new_stock
        locked.save(update_fields=["stock", "updated_at"])
        StockAdjustment.objects.create(
            product=locked, change=delta, stock_after=new_stock,
            reason=reason, note=note, created_by=user,
        )
        self.stock = new_stock
        return new_stock


class ProductImage(TimeStampedModel):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to="products/", blank=True)
    image_url = models.URLField(blank=True, help_text="Use an external URL instead of an upload.")
    alt_text = models.CharField(max_length=180, blank=True)
    is_primary = models.BooleanField(default=False)
    sort_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["-is_primary", "sort_order", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["product"],
                condition=models.Q(is_primary=True),
                name="unique_primary_image_per_product",
            ),
        ]

    def __str__(self):
        return f"Image for {self.product_id}"

    @property
    def url(self) -> str:
        if self.image:
            return self.image.url
        return self.image_url

    def clean(self):
        if not self.image and not self.image_url:
            raise ValidationError("Provide either an uploaded image or an image URL.")

    def save(self, *args, **kwargs):
        with transaction.atomic():
            if self.is_primary:
                ProductImage.objects.filter(
                    product_id=self.product_id, is_primary=True
                ).exclude(pk=self.pk).update(is_primary=False)
            super().save(*args, **kwargs)


class StockAdjustment(models.Model):
    """Append-only inventory ledger (who changed stock, by how much, and why)."""

    class Reason(models.TextChoices):
        RESTOCK = "restock", "Restock"
        SALE = "sale", "Sale"
        CANCELLATION = "cancellation", "Order cancelled / returned"
        CORRECTION = "correction", "Manual correction"
        DAMAGED = "damaged", "Damaged / lost"

    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="stock_adjustments"
    )
    change = models.IntegerField(help_text="Positive adds stock, negative removes it.")
    stock_after = models.PositiveIntegerField()
    reason = models.CharField(max_length=20, choices=Reason.choices)
    note = models.CharField(max_length=255, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="+",
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        constraints = [
            models.CheckConstraint(condition=~models.Q(change=0), name="stock_change_nonzero"),
        ]

    def __str__(self):
        return f"{self.product_id}: {self.change:+d} ({self.reason})"