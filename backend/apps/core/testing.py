"""Shared base class for API tests."""
from django.core.cache import cache
from rest_framework.test import APITestCase as DRFAPITestCase


class APITestCase(DRFAPITestCase):
    def setUp(self):
        super().setUp()
        cache.clear()  # throttle counters live in the cache; reset between tests

    def login_as(self, user):
        """Authenticate the test client as `user` (skips the JWT round-trip)."""
        self.client.force_authenticate(user=user)