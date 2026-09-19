import secrets
import string
from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models, transaction
from django.utils import timezone

from apps.catalog.models import Product
from apps.core.models import TimeStampedModel

from .exceptions import InvalidStatusTransition

_ORDER_ALPHABET = string.ascii_uppercase + string.digits


def generate_order_number() -> str:
    """e.g. TOY-20260919-K7Q2ZP  (date + 6 random chars, uniqueness checked on save)."""
    suffix = "".join(secrets.choice(_ORDER_ALPHABET) for _ in range(6))
    return f"TOY-{timezone.now():%Y%m%d}-{suffix}"


class Order(TimeStampedModel):
    class Status(models.TextChoices):
        PLACED = "placed", "Order placed"
        CONFIRMED = "confirmed", "Confirmed"
        PACKED = "packed", "Packed"
        SHIPPED = "shipped", "Shipped"
        OUT_FOR_DELIVERY = "out_for_delivery", "Out for delivery"
        DELIVERED = "delivered", "Delivered"
        CANCELLED = "cancelled", "Cancelled"

    # Status state machine: which statuses may follow which.
    ALLOWED_TRANSITIONS = {
        Status.PLACED: {Status.CONFIRMED, Status.CANCELLED},
        Status.CONFIRMED: {Status.PACKED, Status.CANCELLED},
        Status.PACKED: {Status.SHIPPED, Status.CANCELLED},
        Status.SHIPPED: {Status.OUT_FOR_DELIVERY},
        Status.OUT_FOR_DELIVERY: {Status.DELIVERED},
        Status.DELIVERED: set(),
        Status.CANCELLED: set(),
    }
    # Statuses in which a *customer* may still cancel their own order.
    CUSTOMER_CANCELLABLE = {Status.PLACED, Status.CONFIRMED}

    order_number = models.CharField(max_length=30, unique=True, editable=False)
    # PROTECT: deactivate users instead of deleting so order history is never lost.
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="orders"
    )
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PLACED, db_index=True
    )

    # Shipping address *snapshot* (copied from Address at checkout time).
    shipping_name = models.CharField(max_length=120)
    shipping_phone = models.CharField(max_length=20)
    shipping_line1 = models.CharField(max_length=255)
    shipping_line2 = models.CharField(max_length=255, blank=True)
    shipping_city = models.CharField(max_length=100)
    shipping_state = models.CharField(max_length=100)
    shipping_postal_code = models.CharField(max_length=12)
    shipping_country = models.CharField(max_length=100)

    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    discount_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    shipping_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total = models.DecimalField(
        max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal("0.00"))]
    )
    customer_note = models.CharField(max_length=500, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["user", "-created_at"])]

    def __str__(self):
        return self.order_number

    def save(self, *args, **kwargs):
        if not self.order_number:
            number = generate_order_number()
            while Order.objects.filter(order_number=number).exists():
                number = generate_order_number()
            self.order_number = number
        super().save(*args, **kwargs)

    # ------------------------------------------------------- state machine
    def can_transition_to(self, new_status: str) -> bool:
        return new_status in self.ALLOWED_TRANSITIONS.get(self.status, set())

    @property
    def is_customer_cancellable(self) -> bool:
        return self.status in self.CUSTOMER_CANCELLABLE

    @property
    def is_paid(self) -> bool:
        return self.payments.filter(status=Payment.Status.SUCCESS).exists()

    @transaction.atomic
    def set_status(self, new_status: str, user=None, note: str = "") -> None:
        """Move the order to `new_status`, validating the transition and logging it."""
        if not self.can_transition_to(new_status):
            raise InvalidStatusTransition(
                f"Cannot change order from '{self.status}' to '{new_status}'."
            )
        self.status = new_status
        self.save(update_fields=["status", "updated_at"])
        OrderStatusHistory.objects.create(
            order=self, status=new_status, note=note, changed_by=user
        )


class OrderItem(models.Model):
    """A purchased line. Name/price are copied so catalog edits never rewrite history."""

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(
        Product, null=True, on_delete=models.SET_NULL, related_name="order_items"
    )
    product_name = models.CharField(max_length=180)
    sku = models.CharField(max_length=40)
    image_url = models.CharField(max_length=500, blank=True)
    list_price = models.DecimalField(max_digits=10, decimal_places=2)
    unit_price = models.DecimalField(
        max_digits=10, decimal_places=2, help_text="Price paid per unit (after discount)."
    )
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])

    class Meta:
        ordering = ["id"]
        constraints = [
            models.CheckConstraint(condition=models.Q(quantity__gte=1), name="order_item_qty_min_1"),
        ]

    def __str__(self):
        return f"{self.quantity} x {self.product_name}"

    @property
    def line_total(self) -> Decimal:
        return self.unit_price * self.quantity


class OrderStatusHistory(models.Model):
    """Timeline shown on the order-tracking page."""

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="status_history")
    status = models.CharField(max_length=20, choices=Order.Status.choices)
    note = models.CharField(max_length=255, blank=True)
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="+",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "id"]
        verbose_name_plural = "order status history"

    def __str__(self):
        return f"{self.order_id}: {self.status}"


class Payment(TimeStampedModel):
    """Payment attempt for an order. Only a mock gateway is used for now."""

    class Method(models.TextChoices):
        CARD = "card", "Credit / debit card"
        WALLET = "wallet", "Digital wallet"
        COD = "cod", "Cash on delivery"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        SUCCESS = "success", "Paid"
        FAILED = "failed", "Failed"
        REFUNDED = "refunded", "Refunded"

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="payments")
    method = models.CharField(max_length=10, choices=Method.choices)
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.PENDING, db_index=True
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    provider = models.CharField(max_length=30, default="mock")
    transaction_id = models.CharField(max_length=64, unique=True, null=True, blank=True)
    failure_reason = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.order_id} {self.method} {self.status}"