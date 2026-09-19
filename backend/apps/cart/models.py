from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models

from apps.catalog.models import Product
from apps.core.models import TimeStampedModel


class Cart(TimeStampedModel):
    """One persistent cart per user."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="cart"
    )

    def __str__(self):
        return f"Cart of {self.user_id}"

    @property
    def item_count(self) -> int:
        return sum(item.quantity for item in self.items.all())

    @property
    def subtotal(self) -> Decimal:
        """Sum of list prices (before discounts)."""
        return sum((i.list_total for i in self.items.all()), Decimal("0.00"))

    @property
    def total(self) -> Decimal:
        """Sum of discounted line totals (before shipping)."""
        return sum((i.line_total for i in self.items.all()), Decimal("0.00"))

    @property
    def discount_total(self) -> Decimal:
        return self.subtotal - self.total

    @property
    def shipping_fee(self) -> Decimal:
        if self.total == 0 or self.total >= Decimal(str(settings.FREE_SHIPPING_THRESHOLD)):
            return Decimal("0.00")
        return Decimal(str(settings.SHIPPING_FEE))

    @property
    def grand_total(self) -> Decimal:
        return self.total + self.shipping_fee


class CartItem(TimeStampedModel):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="+")
    quantity = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])

    class Meta:
        ordering = ["created_at"]
        constraints = [
            models.UniqueConstraint(fields=["cart", "product"], name="unique_product_per_cart"),
            models.CheckConstraint(condition=models.Q(quantity__gte=1), name="cart_qty_min_1"),
        ]

    def __str__(self):
        return f"{self.quantity} x {self.product_id}"

    @property
    def list_total(self) -> Decimal:
        return self.product.price * self.quantity

    @property
    def line_total(self) -> Decimal:
        return self.product.discounted_price * self.quantity