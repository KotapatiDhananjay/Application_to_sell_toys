from decimal import Decimal

from django.db import connection
from django.test.utils import CaptureQueriesContext

from apps.catalog.models import ProductImage
from apps.core.factories import make_category, make_product
from apps.core.testing import APITestCase

PRODUCTS = "/api/products/"
CATEGORIES = "/api/categories/"


def names(response):
    return [p["name"] for p in response.json()["results"]]


class CategoryApiTests(APITestCase):
    def test_lists_only_active_categories_with_active_product_counts(self):
        dolls = make_category("Dolls", sort_order=1)
        make_category("Hidden", is_active=False)
        make_product(dolls)
        make_product(dolls)
        make_product(dolls, is_active=False)
        res = self.client.get(CATEGORIES)
        self.assertEqual(res.status_code, 200)
        data = res.json()  # not paginated: a plain list
        self.assertEqual([c["name"] for c in data], ["Dolls"])
        self.assertEqual(data[0]["product_count"], 2)
        self.assertEqual(data[0]["slug"], "dolls")


class ProductListTests(APITestCase):
    def setUp(self):
        super().setUp()
        self.cars = make_category("Cars")
        self.dolls = make_category("Dolls")

    def test_public_and_paginated_shape(self):
        make_product(self.cars)
        res = self.client.get(PRODUCTS)
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertEqual(set(body), {"count", "next", "previous", "results"})
        self.assertEqual(body["count"], 1)

    def test_card_fields(self):
        make_product(self.cars, name="Race Car", price=Decimal("100.00"), discount_percent=15,
                     stock=3, age_min=3, age_max=8, brand="TurboTrail")
        item = self.client.get(PRODUCTS).json()["results"][0]
        self.assertEqual(item["price"], "100.00")
        self.assertEqual(item["discounted_price"], "85.00")
        self.assertTrue(item["has_discount"])
        self.assertEqual(item["stock_status"], "low_stock")
        self.assertEqual(item["age_range"], "3-8 years")
        self.assertEqual(item["category"]["slug"], "cars")
        self.assertIsNone(item["image"])

    def test_hidden_products_are_excluded(self):
        make_product(self.cars, name="Visible")
        make_product(self.cars, name="Inactive product", is_active=False)
        hidden_cat = make_category("Hidden", is_active=False)
        make_product(hidden_cat, name="In inactive category")
        self.assertEqual(names(self.client.get(PRODUCTS)), ["Visible"])

    def test_image_urls_are_absolute(self):
        product = make_product(self.cars)
        ProductImage.objects.create(product=product, image_url="https://img.test/a.jpg", is_primary=True)
        self.assertEqual(self.client.get(PRODUCTS).json()["results"][0]["image"], "https://img.test/a.jpg")

    def test_search_matches_name_brand_and_category(self):
        make_product(self.cars, name="Rocket Racer", brand="Zoom")
        make_product(self.dolls, name="Rag Doll", brand="Petal")
        self.assertEqual(names(self.client.get(PRODUCTS, {"search": "rocket"})), ["Rocket Racer"])
        self.assertEqual(names(self.client.get(PRODUCTS, {"search": "petal"})), ["Rag Doll"])
        self.assertEqual(names(self.client.get(PRODUCTS, {"search": "dolls"})), ["Rag Doll"])
        self.assertEqual(names(self.client.get(PRODUCTS, {"search": "zzz"})), [])

    def test_filter_by_category_slug(self):
        make_product(self.cars, name="Car A")
        make_product(self.dolls, name="Doll A")
        self.assertEqual(names(self.client.get(PRODUCTS, {"category": "dolls"})), ["Doll A"])

    def test_price_filter_uses_discounted_price(self):
        make_product(self.cars, name="Cheap", price=Decimal("10.00"))
        make_product(self.cars, name="Sale", price=Decimal("100.00"), discount_percent=50)  # pays 50
        make_product(self.cars, name="Pricey", price=Decimal("100.00"))
        self.assertEqual(sorted(names(self.client.get(PRODUCTS, {"max_price": "50"}))), ["Cheap", "Sale"])
        self.assertEqual(sorted(names(self.client.get(PRODUCTS, {"min_price": "50"}))), ["Pricey", "Sale"])
        self.assertEqual(names(self.client.get(PRODUCTS, {"min_price": "20", "max_price": "60"})), ["Sale"])

    def test_price_filter_boundary_matches_displayed_price(self):
        make_product(self.cars, name="Edge", price=Decimal("19.99"), discount_percent=25)  # shows 14.99
        self.assertEqual(names(self.client.get(PRODUCTS, {"max_price": "14.99"})), ["Edge"])
        self.assertEqual(names(self.client.get(PRODUCTS, {"min_price": "15"})), [])

    def test_age_filter(self):
        make_product(self.cars, name="Toddler", age_min=1, age_max=3)
        make_product(self.cars, name="Kids", age_min=3, age_max=8)
        make_product(self.cars, name="Eight plus", age_min=8, age_max=None)
        self.assertEqual(sorted(names(self.client.get(PRODUCTS, {"age": 3}))), ["Kids", "Toddler"])
        self.assertEqual(names(self.client.get(PRODUCTS, {"age": 5})), ["Kids"])
        self.assertEqual(names(self.client.get(PRODUCTS, {"age": 12})), ["Eight plus"])

    def test_in_stock_on_sale_and_featured_switches(self):
        make_product(self.cars, name="Plain", stock=5)
        make_product(self.cars, name="Sold out", stock=0)
        make_product(self.cars, name="Deal", discount_percent=10)
        make_product(self.cars, name="Star", is_featured=True)
        self.assertNotIn("Sold out", names(self.client.get(PRODUCTS, {"in_stock": "true"})))
        self.assertEqual(names(self.client.get(PRODUCTS, {"on_sale": "true"})), ["Deal"])
        self.assertEqual(names(self.client.get(PRODUCTS, {"featured": "true"})), ["Star"])
        # "false" simply means "don't filter"
        self.assertEqual(len(names(self.client.get(PRODUCTS, {"in_stock": "false"}))), 4)

    def test_sorting_by_final_price_and_name(self):
        make_product(self.cars, name="B", price=Decimal("30.00"))
        make_product(self.cars, name="A", price=Decimal("100.00"), discount_percent=80)  # pays 20
        make_product(self.cars, name="C", price=Decimal("25.00"))
        self.assertEqual(names(self.client.get(PRODUCTS, {"ordering": "final_price"})), ["A", "C", "B"])
        self.assertEqual(names(self.client.get(PRODUCTS, {"ordering": "-final_price"})), ["B", "C", "A"])
        self.assertEqual(names(self.client.get(PRODUCTS, {"ordering": "name"})), ["A", "B", "C"])

    def test_default_order_is_newest_first(self):
        make_product(self.cars, name="Old")
        make_product(self.cars, name="New")
        self.assertEqual(names(self.client.get(PRODUCTS)), ["New", "Old"])

    def test_pagination_never_repeats_or_skips_items(self):
        for i in range(7):
            make_product(self.cars, name=f"Same price {i}", price=Decimal("10.00"))
        seen = []
        for page in (1, 2, 3, 4):
            res = self.client.get(PRODUCTS, {"page_size": 2, "page": page, "ordering": "final_price"})
            self.assertEqual(res.status_code, 200)
            seen += [p["id"] for p in res.json()["results"]]
        self.assertEqual(len(seen), 7)
        self.assertEqual(len(set(seen)), 7)

    def test_every_sort_ends_with_an_id_tiebreaker_in_sql(self):
        """Equal sort values must still have a fixed order, or pages can repeat rows."""
        make_product(self.cars)
        for params in ({}, {"ordering": "final_price"}, {"ordering": "-name"}):
            with CaptureQueriesContext(connection) as ctx:
                self.client.get(PRODUCTS, params)
            product_selects = [
                q["sql"] for q in ctx.captured_queries
                if 'FROM "catalog_product"' in q["sql"] and "ORDER BY" in q["sql"]
                and "COUNT(" not in q["sql"]
            ]
            self.assertTrue(product_selects, params)
            for sql in product_selects:
                order_by = sql.split("ORDER BY")[-1]
                self.assertIn('"catalog_product"."id" DESC', order_by, params)

    def test_page_size_is_capped(self):
        for _ in range(3):
            make_product(self.cars)
        self.assertEqual(len(self.client.get(PRODUCTS, {"page_size": 2}).json()["results"]), 2)
        self.assertEqual(self.client.get(PRODUCTS, {"page_size": 9999}).json()["count"], 3)

    def test_bad_filter_value_is_a_400_not_a_crash(self):
        res = self.client.get(PRODUCTS, {"min_price": "abc"})
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.json()["error"]["code"], 400)

    def test_query_count_does_not_grow_with_number_of_products(self):
        for _ in range(3):
            ProductImage.objects.create(product=make_product(self.cars), image_url="https://img.test/x.jpg")
        with CaptureQueriesContext(connection) as few:
            self.client.get(PRODUCTS)
        for _ in range(9):
            ProductImage.objects.create(product=make_product(self.cars), image_url="https://img.test/y.jpg")
        with CaptureQueriesContext(connection) as many:
            self.client.get(PRODUCTS, {"page_size": 12})
        self.assertEqual(len(few), len(many))


class ProductDetailTests(APITestCase):
    def setUp(self):
        super().setUp()
        self.cat = make_category("Cars")

    def test_detail_by_slug(self):
        product = make_product(self.cat, name="Rocket Racer", description="Fast!")
        ProductImage.objects.create(product=product, image_url="https://img.test/1.jpg", is_primary=True)
        ProductImage.objects.create(product=product, image_url="https://img.test/2.jpg")
        res = self.client.get(f"{PRODUCTS}rocket-racer/")
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertEqual(body["name"], "Rocket Racer")
        self.assertEqual(body["description"], "Fast!")
        self.assertEqual([i["url"] for i in body["images"]],
                         ["https://img.test/1.jpg", "https://img.test/2.jpg"])
        self.assertEqual(body["image"], "https://img.test/1.jpg")

    def test_related_products_are_same_category_and_exclude_self(self):
        main = make_product(self.cat, name="Main")
        make_product(self.cat, name="Sibling")
        make_product(self.cat, name="Hidden sibling", is_active=False)
        make_product(make_category("Dolls"), name="Other category")
        related = self.client.get(f"{PRODUCTS}{main.slug}/").json()["related_products"]
        self.assertEqual([p["name"] for p in related], ["Sibling"])

    def test_unknown_or_inactive_product_is_404(self):
        make_product(self.cat, name="Gone", is_active=False)
        self.assertEqual(self.client.get(f"{PRODUCTS}gone/").status_code, 404)
        res = self.client.get(f"{PRODUCTS}does-not-exist/")
        self.assertEqual(res.status_code, 404)
        self.assertEqual(res.json()["error"]["code"], 404)