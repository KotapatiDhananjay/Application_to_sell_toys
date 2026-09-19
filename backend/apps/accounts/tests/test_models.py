from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase

from apps.accounts.models import Address, User
from apps.core.factories import make_user


def make_address(user, **kwargs):
    data = dict(
        user=user, full_name="Sam Buyer", phone="+1 555 123 4567",
        line1="1 Toy Lane", city="Springfield", state="IL",
        postal_code="62701", country="USA",
    )
    data.update(kwargs)
    return Address.objects.create(**data)


class UserModelTests(TestCase):
    def test_create_user_normalizes_email_and_hashes_password(self):
        user = User.objects.create_user(email="Sam@EXAMPLE.com", password="Str0ng-pass!")
        self.assertEqual(user.email, "sam@example.com")
        self.assertNotEqual(user.password, "Str0ng-pass!")
        self.assertTrue(user.check_password("Str0ng-pass!"))
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_admin)

    def test_email_is_required(self):
        with self.assertRaises(ValueError):
            User.objects.create_user(email="", password="x")

    def test_email_must_be_unique(self):
        make_user(email="dup@example.com")
        with self.assertRaises(IntegrityError), transaction.atomic():
            make_user(email="dup@example.com")

    def test_create_superuser(self):
        admin = User.objects.create_superuser(email="root@example.com", password="Str0ng-pass!")
        self.assertTrue(admin.is_staff and admin.is_superuser and admin.is_admin)

    def test_superuser_flags_cannot_be_disabled(self):
        with self.assertRaises(ValueError):
            User.objects.create_superuser("a@example.com", "x", is_staff=False)


class AddressModelTests(TestCase):
    def setUp(self):
        self.user = make_user()

    def test_first_address_becomes_default(self):
        addr = make_address(self.user)
        self.assertTrue(addr.is_default)

    def test_new_default_demotes_previous_default(self):
        first = make_address(self.user)
        second = make_address(self.user, is_default=True, label="work")
        first.refresh_from_db()
        self.assertFalse(first.is_default)
        self.assertTrue(second.is_default)
        self.assertEqual(Address.objects.filter(user=self.user, is_default=True).count(), 1)

    def test_non_default_second_address_keeps_first_default(self):
        first = make_address(self.user)
        make_address(self.user)
        first.refresh_from_db()
        self.assertTrue(first.is_default)

    def test_defaults_are_per_user(self):
        other = make_user()
        a, b = make_address(self.user), make_address(other)
        self.assertTrue(a.is_default and b.is_default)

    def test_phone_validation(self):
        addr = Address(
            user=self.user, full_name="X", phone="abc", line1="l", city="c",
            state="s", postal_code="1", country="c",
        )
        with self.assertRaises(ValidationError) as ctx:
            addr.full_clean()
        self.assertIn("phone", ctx.exception.message_dict)

    def test_snapshot_contains_shipping_fields(self):
        snap = make_address(self.user).as_snapshot()
        self.assertEqual(snap["shipping_name"], "Sam Buyer")
        self.assertEqual(snap["shipping_postal_code"], "62701")