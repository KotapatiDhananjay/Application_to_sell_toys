from django.conf import settings
from django.db import models

from apps.catalog.models import Product
from apps.core.models import TimeStampedModel


class WishlistItem(TimeStampedModel):
    """A product a user saved for later. One row per (user, product)."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="wishlist_items"
    )
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="wishlisted_by")

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["user", "product"], name="unique_wishlist_item"),
        ]

    def __str__(self):
        return f"{self.user_id} -> {self.product_id}"