from django.test import TestCase
from rest_framework.test import APIClient


class HealthCheckTests(TestCase):
    def test_health_endpoint_is_public(self):
        res = APIClient().get("/api/health/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json(), {"status": "ok"})

    def test_errors_use_uniform_shape(self):
        res = APIClient().post("/api/health/", {})  # POST not allowed
        self.assertEqual(res.status_code, 405)
        body = res.json()
        self.assertEqual(body["error"]["code"], 405)
        self.assertIn("message", body["error"])