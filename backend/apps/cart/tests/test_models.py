from decimal import Decimal

from django.db import IntegrityError, transaction
from django.test import TestCase, override_settings

from apps.cart.models import Cart, CartItem
from apps.core.factories import make_product, make_user


@override_settings(SHIPPING_FEE=5.99, FREE_SHIPPING_THRESHOLD=50)
class CartTests(TestCase):
    def setUp(self):
        self.cart = Cart.objects.create(user=make_user())

    def test_empty_cart_totals_are_zero(self):
        self.assertEqual(self.cart.total, Decimal("0.00"))
        self.assertEqual(self.cart.shipping_fee, Decimal("0.00"))
        self.assertEqual(self.cart.item_count, 0)

    def test_totals_with_discounts(self):
        a = make_product(price=Decimal("20.00"), discount_percent=10)  # 18.00
        b = make_product(price=Decimal("10.00"))
        CartItem.objects.create(cart=self.cart, product=a, quantity=2)
        CartItem.objects.create(cart=self.cart, product=b, quantity=1)
        self.assertEqual(self.cart.item_count, 3)
        self.assertEqual(self.cart.subtotal, Decimal("50.00"))
        self.assertEqual(self.cart.total, Decimal("46.00"))
        self.assertEqual(self.cart.discount_total, Decimal("4.00"))

    def test_shipping_charged_below_threshold(self):
        CartItem.objects.create(cart=self.cart, product=make_product(price=Decimal("30")), quantity=1)
        self.assertEqual(self.cart.shipping_fee, Decimal("5.99"))
        self.assertEqual(self.cart.grand_total, Decimal("35.99"))

    def test_free_shipping_at_threshold(self):
        CartItem.objects.create(cart=self.cart, product=make_product(price=Decimal("50")), quantity=1)
        self.assertEqual(self.cart.shipping_fee, Decimal("0.00"))

    def test_product_only_once_per_cart(self):
        p = make_product()
        CartItem.objects.create(cart=self.cart, product=p)
        with self.assertRaises(IntegrityError), transaction.atomic():
            CartItem.objects.create(cart=self.cart, product=p)

    def test_quantity_must_be_at_least_one(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            CartItem.objects.create(cart=self.cart, product=make_product(), quantity=0)

    def test_one_cart_per_user(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            Cart.objects.create(user=self.cart.user)