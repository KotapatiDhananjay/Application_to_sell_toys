"""Tiny helpers for building test data (used by every app's tests)."""
import itertools
from decimal import Decimal

from django.contrib.auth import get_user_model

from apps.catalog.models import Category, Product

_counter = itertools.count(1)


def make_user(email=None, password="Str0ng-pass!", **kwargs):
    n = next(_counter)
    return get_user_model().objects.create_user(
        email=email or f"user{n}@example.com",
        password=password,
        first_name=kwargs.pop("first_name", "Test"),
        last_name=kwargs.pop("last_name", "User"),
        **kwargs,
    )


def make_category(name=None, **kwargs):
    return Category.objects.create(name=name or f"Category {next(_counter)}", **kwargs)


def make_product(category=None, **kwargs):
    n = next(_counter)
    defaults = dict(
        category=category or make_category(),
        name=f"Toy {n}",
        sku=f"SKU-{n:05d}",
        price=Decimal("20.00"),
        stock=10,
        age_min=3,
        age_max=8,
    )
    defaults.update(kwargs)
    return Product.objects.create(**defaults)