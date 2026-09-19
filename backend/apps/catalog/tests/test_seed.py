import shutil
import tempfile
from pathlib import Path

from django.core.management import call_command
from django.test import TestCase, override_settings

from apps.catalog.models import Category, Product, ProductImage
from apps.catalog.views import public_products

MEDIA = tempfile.mkdtemp()


@override_settings(MEDIA_ROOT=MEDIA)
class SeedDataTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA, ignore_errors=True)

    def seed(self):
        call_command("seed_data", verbosity=0)

    def test_creates_six_categories_and_24_products(self):
        self.seed()
        self.assertEqual(Category.objects.count(), 6)
        self.assertEqual(Product.objects.count(), 24)
        for category in Category.objects.all():
            self.assertEqual(category.products.count(), 4, category.name)

    def test_every_product_has_a_real_image_file(self):
        self.seed()
        self.assertEqual(ProductImage.objects.count(), 24)
        for image in ProductImage.objects.all():
            self.assertTrue(image.is_primary)
            self.assertTrue(Path(image.image.path).exists())

    def test_running_twice_creates_no_duplicates(self):
        self.seed()
        self.seed()
        self.assertEqual(Product.objects.count(), 24)
        self.assertEqual(ProductImage.objects.count(), 24)

    def test_rerun_does_not_overwrite_admin_edits(self):
        self.seed()
        Product.objects.filter(sku="EDU-001").update(price="1.23", stock=999)
        self.seed()
        product = Product.objects.get(sku="EDU-001")
        self.assertEqual((str(product.price), product.stock), ("1.23", 999))

    def test_data_is_varied_enough_to_demo_the_ui(self):
        self.seed()
        self.assertEqual(Product.objects.filter(stock=0).count(), 1)                      # sold out
        self.assertGreaterEqual(Product.objects.filter(stock__gt=0, stock__lte=5).count(), 2)  # low stock
        self.assertGreaterEqual(Product.objects.filter(discount_percent__gt=0).count(), 8)
        self.assertEqual(Product.objects.filter(is_featured=True).count(), 8)
        self.assertGreaterEqual(Product.objects.filter(age_max__isnull=True).count(), 3)

    def test_database_price_matches_python_price_for_every_product(self):
        """The filter/sort price (SQL) must equal the displayed price (Python)."""
        self.seed()
        for product in public_products():
            self.assertEqual(product.final_price, product.discounted_price, product.sku)