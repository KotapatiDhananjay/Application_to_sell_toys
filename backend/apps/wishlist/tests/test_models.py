from django.db import IntegrityError, transaction
from django.test import TestCase

from apps.core.factories import make_product, make_user
from apps.wishlist.models import WishlistItem


class WishlistTests(TestCase):
    def test_product_can_be_wishlisted_once_per_user(self):
        user, product = make_user(), make_product()
        WishlistItem.objects.create(user=user, product=product)
        with self.assertRaises(IntegrityError), transaction.atomic():
            WishlistItem.objects.create(user=user, product=product)

    def test_different_users_can_wishlist_same_product(self):
        product = make_product()
        WishlistItem.objects.create(user=make_user(), product=product)
        WishlistItem.objects.create(user=make_user(), product=product)
        self.assertEqual(product.wishlisted_by.count(), 2)

    def test_deleting_product_removes_wishlist_rows(self):
        user, product = make_user(), make_product()
        WishlistItem.objects.create(user=user, product=product)
        product.delete()
        self.assertEqual(WishlistItem.objects.count(), 0)