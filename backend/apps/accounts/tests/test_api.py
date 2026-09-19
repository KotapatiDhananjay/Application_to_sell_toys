from django.contrib.auth import get_user_model

from apps.accounts.models import Address
from apps.core.factories import make_user
from apps.core.testing import APITestCase

User = get_user_model()

REGISTER = "/api/auth/register/"
LOGIN = "/api/auth/login/"
REFRESH = "/api/auth/token/refresh/"
ME = "/api/auth/me/"
ADDRESSES = "/api/addresses/"

VALID_SIGNUP = {
    "email": "sam@example.com",
    "first_name": "Sam",
    "last_name": "Buyer",
    "phone": "+1 555 123 4567",
    "password": "Str0ng-pass!",
    "password_confirm": "Str0ng-pass!",
}


class RegisterTests(APITestCase):
    def test_register_creates_user_and_returns_tokens(self):
        res = self.client.post(REGISTER, VALID_SIGNUP, format="json")
        self.assertEqual(res.status_code, 201)
        body = res.json()
        self.assertEqual(body["user"]["email"], "sam@example.com")
        self.assertIn("access", body)
        self.assertIn("refresh", body)
        self.assertNotIn("password", body["user"])
        user = User.objects.get(email="sam@example.com")
        self.assertTrue(user.check_password("Str0ng-pass!"))
        self.assertFalse(user.is_staff)

    def test_email_is_lowercased(self):
        res = self.client.post(REGISTER, {**VALID_SIGNUP, "email": "  Sam@Example.COM "}, format="json")
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.json()["user"]["email"], "sam@example.com")

    def test_duplicate_email_rejected_case_insensitively(self):
        make_user(email="sam@example.com")
        res = self.client.post(REGISTER, {**VALID_SIGNUP, "email": "SAM@example.com"}, format="json")
        self.assertEqual(res.status_code, 400)
        self.assertIn("email", res.json()["error"]["details"])

    def test_password_mismatch_rejected(self):
        res = self.client.post(REGISTER, {**VALID_SIGNUP, "password_confirm": "Different-pass1"}, format="json")
        self.assertEqual(res.status_code, 400)
        self.assertIn("password_confirm", res.json()["error"]["details"])

    def test_weak_passwords_rejected(self):
        for weak in ["short1!", "12345678901", "password"]:
            res = self.client.post(
                REGISTER, {**VALID_SIGNUP, "password": weak, "password_confirm": weak}, format="json"
            )
            self.assertEqual(res.status_code, 400, weak)
            self.assertIn("password", res.json()["error"]["details"])
        self.assertEqual(User.objects.count(), 0)

    def test_required_fields(self):
        res = self.client.post(REGISTER, {}, format="json")
        self.assertEqual(res.status_code, 400)
        details = res.json()["error"]["details"]
        for field in ["email", "first_name", "last_name", "password", "password_confirm"]:
            self.assertIn(field, details)

    def test_cannot_register_as_admin(self):
        res = self.client.post(REGISTER, {**VALID_SIGNUP, "is_staff": True, "is_superuser": True}, format="json")
        self.assertEqual(res.status_code, 201)
        user = User.objects.get(email="sam@example.com")
        self.assertFalse(user.is_staff or user.is_superuser)


class LoginTests(APITestCase):
    def setUp(self):
        super().setUp()
        self.user = make_user(email="sam@example.com", password="Str0ng-pass!")

    def test_login_returns_tokens_and_profile(self):
        res = self.client.post(LOGIN, {"email": "sam@example.com", "password": "Str0ng-pass!"}, format="json")
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertTrue(body["access"] and body["refresh"])
        self.assertEqual(body["user"]["email"], "sam@example.com")

    def test_login_is_case_insensitive_on_email(self):
        res = self.client.post(LOGIN, {"email": " SAM@Example.com", "password": "Str0ng-pass!"}, format="json")
        self.assertEqual(res.status_code, 200)

    def test_wrong_password_gives_401_in_uniform_format(self):
        res = self.client.post(LOGIN, {"email": "sam@example.com", "password": "nope"}, format="json")
        self.assertEqual(res.status_code, 401)
        error = res.json()["error"]
        self.assertEqual(error["code"], 401)
        self.assertIn("message", error)

    def test_inactive_user_cannot_login(self):
        self.user.is_active = False
        self.user.save()
        res = self.client.post(LOGIN, {"email": "sam@example.com", "password": "Str0ng-pass!"}, format="json")
        self.assertEqual(res.status_code, 401)

    def test_access_token_works_on_protected_endpoint(self):
        tokens = self.client.post(LOGIN, {"email": "sam@example.com", "password": "Str0ng-pass!"}, format="json").json()
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
        res = self.client.get(ME)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["email"], "sam@example.com")

    def test_garbage_token_is_rejected(self):
        self.client.credentials(HTTP_AUTHORIZATION="Bearer not-a-real-token")
        self.assertEqual(self.client.get(ME).status_code, 401)

    def test_refresh_returns_new_access_token(self):
        tokens = self.client.post(LOGIN, {"email": "sam@example.com", "password": "Str0ng-pass!"}, format="json").json()
        res = self.client.post(REFRESH, {"refresh": tokens["refresh"]}, format="json")
        self.assertEqual(res.status_code, 200)
        self.assertIn("access", res.json())

    def test_login_is_rate_limited(self):
        for _ in range(10):
            self.client.post(LOGIN, {"email": "sam@example.com", "password": "wrong"}, format="json")
        res = self.client.post(LOGIN, {"email": "sam@example.com", "password": "wrong"}, format="json")
        self.assertEqual(res.status_code, 429)
        self.assertEqual(res.json()["error"]["code"], 429)
        self.assertIn("Retry-After", res.headers)


class ProfileTests(APITestCase):
    def test_me_requires_login(self):
        self.assertEqual(self.client.get(ME).status_code, 401)

    def test_update_profile(self):
        user = make_user()
        self.login_as(user)
        res = self.client.patch(ME, {"first_name": "Alex", "phone": "+44 20 7946 0958"}, format="json")
        self.assertEqual(res.status_code, 200)
        user.refresh_from_db()
        self.assertEqual((user.first_name, user.phone), ("Alex", "+44 20 7946 0958"))

    def test_email_and_admin_flag_cannot_be_changed(self):
        user = make_user(email="keep@example.com")
        self.login_as(user)
        self.client.patch(ME, {"email": "new@example.com", "is_admin": True, "is_staff": True}, format="json")
        user.refresh_from_db()
        self.assertEqual(user.email, "keep@example.com")
        self.assertFalse(user.is_staff)

    def test_invalid_phone_rejected(self):
        self.login_as(make_user())
        res = self.client.patch(ME, {"phone": "abc"}, format="json")
        self.assertEqual(res.status_code, 400)
        self.assertIn("phone", res.json()["error"]["details"])


ADDRESS = {
    "label": "home", "full_name": "Sam Buyer", "phone": "+1 555 123 4567",
    "line1": "1 Toy Lane", "line2": "", "city": "Springfield", "state": "IL",
    "postal_code": "62701", "country": "USA",
}


class AddressApiTests(APITestCase):
    def setUp(self):
        super().setUp()
        self.user = make_user()
        self.login_as(self.user)

    def test_requires_login(self):
        self.client.force_authenticate(user=None)
        self.assertEqual(self.client.get(ADDRESSES).status_code, 401)
        self.assertEqual(self.client.post(ADDRESSES, ADDRESS, format="json").status_code, 401)

    def test_first_address_becomes_default(self):
        res = self.client.post(ADDRESSES, ADDRESS, format="json")
        self.assertEqual(res.status_code, 201)
        self.assertTrue(res.json()["is_default"])

    def test_list_is_a_plain_array_of_own_addresses_only(self):
        mine = self.client.post(ADDRESSES, ADDRESS, format="json").json()
        Address.objects.create(user=make_user(), **{k: v for k, v in ADDRESS.items() if k != "label"})
        res = self.client.get(ADDRESSES)
        self.assertEqual(res.status_code, 200)
        self.assertEqual([a["id"] for a in res.json()], [mine["id"]])

    def test_cannot_touch_another_users_address(self):
        other = Address.objects.create(user=make_user(), **{k: v for k, v in ADDRESS.items() if k != "label"})
        url = f"{ADDRESSES}{other.id}/"
        self.assertEqual(self.client.get(url).status_code, 404)
        self.assertEqual(self.client.patch(url, {"city": "Hacked"}, format="json").status_code, 404)
        self.assertEqual(self.client.delete(url).status_code, 404)
        other.refresh_from_db()
        self.assertNotEqual(other.city, "Hacked")

    def test_user_field_cannot_be_forged(self):
        other = make_user()
        res = self.client.post(ADDRESSES, {**ADDRESS, "user": other.id}, format="json")
        self.assertEqual(res.status_code, 201)
        self.assertEqual(Address.objects.get(pk=res.json()["id"]).user, self.user)

    def test_validation_errors(self):
        res = self.client.post(ADDRESSES, {"phone": "abc"}, format="json")
        self.assertEqual(res.status_code, 400)
        details = res.json()["error"]["details"]
        for field in ["full_name", "phone", "line1", "city", "state", "postal_code", "country"]:
            self.assertIn(field, details)

    def test_update_address(self):
        created = self.client.post(ADDRESSES, ADDRESS, format="json").json()
        res = self.client.patch(f"{ADDRESSES}{created['id']}/", {"city": "Shelbyville"}, format="json")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["city"], "Shelbyville")

    def test_set_default_switches_default(self):
        first = self.client.post(ADDRESSES, ADDRESS, format="json").json()
        second = self.client.post(ADDRESSES, {**ADDRESS, "label": "work"}, format="json").json()
        self.assertFalse(second["is_default"])
        res = self.client.post(f"{ADDRESSES}{second['id']}/set-default/")
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.json()["is_default"])
        self.assertFalse(Address.objects.get(pk=first["id"]).is_default)
        self.assertEqual(Address.objects.filter(user=self.user, is_default=True).count(), 1)

    def test_cannot_unset_the_only_default(self):
        created = self.client.post(ADDRESSES, ADDRESS, format="json").json()
        res = self.client.patch(f"{ADDRESSES}{created['id']}/", {"is_default": False}, format="json")
        self.assertEqual(res.status_code, 400)
        self.assertTrue(Address.objects.get(pk=created["id"]).is_default)

    def test_deleting_default_promotes_another(self):
        first = self.client.post(ADDRESSES, ADDRESS, format="json").json()
        second = self.client.post(ADDRESSES, {**ADDRESS, "label": "work"}, format="json").json()
        self.assertEqual(self.client.delete(f"{ADDRESSES}{first['id']}/").status_code, 204)
        self.assertTrue(Address.objects.get(pk=second["id"]).is_default)

    def test_deleting_last_address_is_fine(self):
        only = self.client.post(ADDRESSES, ADDRESS, format="json").json()
        self.assertEqual(self.client.delete(f"{ADDRESSES}{only['id']}/").status_code, 204)
        self.assertEqual(self.client.get(ADDRESSES).json(), [])