from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase

from apps.catalog.exceptions import InsufficientStockError
from apps.catalog.models import Category, ProductImage, StockAdjustment
from apps.core.factories import make_category, make_product, make_user


class CategoryTests(TestCase):
    def test_slug_generated_from_name(self):
        self.assertEqual(Category.objects.create(name="Action Figures").slug, "action-figures")


class ProductPricingTests(TestCase):
    def test_no_discount(self):
        p = make_product(price=Decimal("20.00"), discount_percent=0)
        self.assertFalse(p.has_discount)
        self.assertEqual(p.discounted_price, Decimal("20.00"))

    def test_discount_applied(self):
        p = make_product(price=Decimal("100.00"), discount_percent=15)
        self.assertTrue(p.has_discount)
        self.assertEqual(p.discounted_price, Decimal("85.00"))
        self.assertEqual(p.savings, Decimal("15.00"))

    def test_discount_rounds_half_up(self):
        p = make_product(price=Decimal("19.99"), discount_percent=25)  # 14.9925
        self.assertEqual(p.discounted_price, Decimal("14.99"))
        p = make_product(price=Decimal("0.10"), discount_percent=50)  # 0.05
        self.assertEqual(p.discounted_price, Decimal("0.05"))


class ProductMetaTests(TestCase):
    def test_slug_is_unique_for_duplicate_names(self):
        cat = make_category()
        a = make_product(cat, name="Wooden Train", sku="A1")
        b = make_product(cat, name="Wooden Train", sku="A2")
        self.assertEqual(a.slug, "wooden-train")
        self.assertEqual(b.slug, "wooden-train-2")

    def test_age_range_labels(self):
        self.assertEqual(make_product(age_min=3, age_max=8).age_range_label, "3-8 years")
        self.assertEqual(make_product(age_min=8, age_max=None).age_range_label, "8+ years")
        self.assertEqual(make_product(age_min=5, age_max=5).age_range_label, "5 years")

    def test_stock_status(self):
        self.assertEqual(make_product(stock=0).stock_status, "out_of_stock")
        self.assertEqual(make_product(stock=3, low_stock_threshold=5).stock_status, "low_stock")
        self.assertEqual(make_product(stock=50).stock_status, "in_stock")

    def test_clean_rejects_inverted_age_range(self):
        p = make_product()
        p.age_min, p.age_max = 10, 4
        with self.assertRaises(ValidationError):
            p.clean()

    def test_db_rejects_non_positive_price(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            make_product(price=Decimal("0"))

    def test_db_rejects_bad_age_range(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            make_product(age_min=10, age_max=4)

    def test_discount_validator_caps_at_90(self):
        p = make_product()
        p.discount_percent = 95
        with self.assertRaises(ValidationError):
            p.full_clean()


class InventoryTests(TestCase):
    def setUp(self):
        self.product = make_product(stock=10)
        self.admin = make_user()

    def test_restock_increases_stock_and_logs(self):
        new = self.product.adjust_stock(5, "restock", user=self.admin, note="PO-1")
        self.product.refresh_from_db()
        self.assertEqual((new, self.product.stock), (15, 15))
        log = StockAdjustment.objects.get()
        self.assertEqual((log.change, log.stock_after, log.reason), (5, 15, "restock"))
        self.assertEqual(log.created_by, self.admin)

    def test_sale_decreases_stock(self):
        self.product.adjust_stock(-4, "sale")
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 6)

    def test_cannot_oversell(self):
        with self.assertRaises(InsufficientStockError) as ctx:
            self.product.adjust_stock(-11, "sale")
        self.assertEqual(ctx.exception.available, 10)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 10)
        self.assertEqual(StockAdjustment.objects.count(), 0)

    def test_can_sell_exact_remaining_stock(self):
        self.product.adjust_stock(-10, "sale")
        self.product.refresh_from_db()
        self.assertFalse(self.product.in_stock)

    def test_zero_change_rejected_by_db(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            self.product.adjust_stock(0, "correction")


class ProductImageTests(TestCase):
    def setUp(self):
        self.product = make_product()

    def test_url_prefers_external_url_when_no_upload(self):
        img = ProductImage.objects.create(product=self.product, image_url="https://x.test/a.jpg")
        self.assertEqual(img.url, "https://x.test/a.jpg")

    def test_only_one_primary_image(self):
        a = ProductImage.objects.create(product=self.product, image_url="https://x.test/a.jpg", is_primary=True)
        b = ProductImage.objects.create(product=self.product, image_url="https://x.test/b.jpg", is_primary=True)
        a.refresh_from_db()
        self.assertFalse(a.is_primary)
        self.assertTrue(b.is_primary)
        self.assertEqual(self.product.primary_image_url, "https://x.test/b.jpg")

    def test_requires_some_image_source(self):
        with self.assertRaises(ValidationError):
            ProductImage(product=self.product).full_clean()