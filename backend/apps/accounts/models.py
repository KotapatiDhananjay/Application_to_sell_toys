from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator
from django.db import models, transaction

from apps.core.models import TimeStampedModel

from .managers import UserManager

phone_validator = RegexValidator(
    regex=r"^\+?[0-9\s\-]{7,15}$",
    message="Enter a valid phone number (7-15 digits, optional leading +).",
)


class User(AbstractUser):
    """Custom user: email is the login identifier, no username.

    Admin access is controlled by `is_staff` (exposed as `is_admin`).
    """

    username = None
    email = models.EmailField("email address", unique=True)
    phone = models.CharField(max_length=20, blank=True, validators=[phone_validator])

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["first_name", "last_name"]

    objects = UserManager()

    class Meta:
        ordering = ["-date_joined"]

    def __str__(self):
        return self.email

    @property
    def is_admin(self) -> bool:
        return self.is_staff

    @property
    def full_name(self) -> str:
        return self.get_full_name() or self.email


class Address(TimeStampedModel):
    """A saved shipping address. A user has at most one default address."""

    class Label(models.TextChoices):
        HOME = "home", "Home"
        WORK = "work", "Work"
        OTHER = "other", "Other"

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="addresses")
    label = models.CharField(max_length=10, choices=Label.choices, default=Label.HOME)
    full_name = models.CharField(max_length=120)
    phone = models.CharField(max_length=20, validators=[phone_validator])
    line1 = models.CharField("address line 1", max_length=255)
    line2 = models.CharField("address line 2", max_length=255, blank=True)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=12)
    country = models.CharField(max_length=100)
    is_default = models.BooleanField(default=False)

    class Meta:
        ordering = ["-is_default", "-created_at"]
        verbose_name_plural = "addresses"
        constraints = [
            # DB-level guarantee: at most one default address per user.
            models.UniqueConstraint(
                fields=["user"],
                condition=models.Q(is_default=True),
                name="unique_default_address_per_user",
            ),
        ]

    def __str__(self):
        return f"{self.full_name} - {self.city} ({self.get_label_display()})"

    def save(self, *args, **kwargs):
        with transaction.atomic():
            # First address a user saves becomes the default automatically.
            if not self.pk and not Address.objects.filter(user_id=self.user_id).exists():
                self.is_default = True
            # Demote any other default *before* saving so the constraint holds.
            if self.is_default:
                Address.objects.filter(user_id=self.user_id, is_default=True).exclude(
                    pk=self.pk
                ).update(is_default=False)
            super().save(*args, **kwargs)

    def as_snapshot(self) -> dict:
        """Plain-dict copy stored on an Order so later edits don't alter history."""
        return {
            "shipping_name": self.full_name,
            "shipping_phone": self.phone,
            "shipping_line1": self.line1,
            "shipping_line2": self.line2,
            "shipping_city": self.city,
            "shipping_state": self.state,
            "shipping_postal_code": self.postal_code,
            "shipping_country": self.country,
        }