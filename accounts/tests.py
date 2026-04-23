from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from accounts.models import FarmerProfile

User = get_user_model()


def make_user(email="test@test.com", password="pass1234", role="customer", verified=True):
    user = User.objects.create_user(email=email, password=password, role=role)
    if verified:
        user.is_active = True
        user.is_verified = True
        user.save(update_fields=["is_active", "is_verified"])
    return user


def make_farmer(email="farmer@test.com", password="pass1234", verified_profile=False):
    user = make_user(email=email, password=password, role="farmer")
    profile, _ = FarmerProfile.objects.get_or_create(user=user)
    if verified_profile:
        profile.is_verified = True
        profile.lat = 42.87
        profile.lon = 74.59
        profile.farm_name = "Test Farm"
        profile.save()
    return user


class UserModelTest(TestCase):

    def test_create_user_email_normalized(self):
        user = User.objects.create_user(email="TEST@EXAMPLE.COM", password="pass")
        self.assertEqual(user.email, "test@example.com")

    def test_create_user_inactive_by_default(self):
        user = User.objects.create_user(email="u@u.com", password="pass")
        self.assertFalse(user.is_active)
        self.assertFalse(user.is_verified)

    def test_activation_code_generated(self):
        user = User.objects.create_user(email="u2@u.com", password="pass")
        self.assertTrue(user.activation_code.isdigit())
        self.assertEqual(len(user.activation_code), 6)

    def test_generate_activation_code(self):
        user = make_user()
        old_code = user.activation_code
        new_code = user.generate_activation_code()
        self.assertEqual(len(new_code), 6)

    def test_superuser_is_active_and_verified(self):
        admin = User.objects.create_superuser(email="admin@a.com", password="pass")
        self.assertTrue(admin.is_active)
        self.assertTrue(admin.is_verified)
        self.assertTrue(admin.is_superuser)

    def test_farmer_profile_created_on_register(self):
        user = make_farmer()
        self.assertTrue(FarmerProfile.objects.filter(user=user).exists())


class RegisterAPITest(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.url = "/api/accounts/register/"

    def test_register_customer(self):
        res = self.client.post(self.url, {
            "email": "new@test.com",
            "password": "pass1234",
            "role": "customer"
        })
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertIn("email", res.data)

    def test_register_farmer_creates_profile(self):
        res = self.client.post(self.url, {
            "email": "farmer@test.com",
            "password": "pass1234",
            "role": "farmer"
        })
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        user = User.objects.get(email="farmer@test.com")
        self.assertTrue(FarmerProfile.objects.filter(user=user).exists())

    def test_register_duplicate_email(self):
        make_user(email="dup@test.com")
        res = self.client.post(self.url, {
            "email": "dup@test.com",
            "password": "pass1234"
        })
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_short_password(self):
        res = self.client.post(self.url, {
            "email": "short@test.com",
            "password": "123"
        })
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)


class VerifyEmailAPITest(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.url = "/api/accounts/verify/"

    def test_verify_correct_code(self):
        user = User.objects.create_user(email="v@test.com", password="pass1234")
        code = user.activation_code
        res = self.client.post(self.url, {"email": "v@test.com", "code": code})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        user.refresh_from_db()
        self.assertTrue(user.is_verified)
        self.assertTrue(user.is_active)

    def test_verify_wrong_code(self):
        User.objects.create_user(email="v2@test.com", password="pass1234")
        res = self.client.post(self.url, {"email": "v2@test.com", "code": "000000"})
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_verify_already_verified(self):
        user = make_user(email="v3@test.com")
        res = self.client.post(self.url, {"email": "v3@test.com", "code": user.activation_code})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("уже", res.data["message"])


class LoginAPITest(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.url = "/api/accounts/login/"
        self.user = make_user(email="login@test.com", password="pass1234")

    def test_login_success(self):
        res = self.client.post(self.url, {
            "email": "login@test.com",
            "password": "pass1234"
        })
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("access", res.data)
        self.assertIn("refresh", res.data)

    def test_login_wrong_password(self):
        res = self.client.post(self.url, {
            "email": "login@test.com",
            "password": "wrongpass"
        })
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_login_unverified_user(self):
        user = User.objects.create_user(email="unverified@test.com", password="pass1234")
        res = self.client.post(self.url, {
            "email": "unverified@test.com",
            "password": "pass1234"
        })
        # Неактивный пользователь не должен получить токен
        self.assertNotEqual(res.status_code, status.HTTP_200_OK)


class MeAPITest(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.url = "/api/accounts/me/"
        self.user = make_user(email="me@test.com")

    def _auth(self):
        res = self.client.post("/api/accounts/login/", {
            "email": "me@test.com", "password": "pass1234"
        })
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {res.data['access']}")

    def test_me_authenticated(self):
        self._auth()
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["email"], "me@test.com")

    def test_me_unauthenticated(self):
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class FarmerProfileAPITest(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.farmer = make_farmer(email="fp@test.com")

    def _auth(self):
        res = self.client.post("/api/accounts/login/", {
            "email": "fp@test.com", "password": "pass1234"
        })
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {res.data['access']}")

    def test_update_farmer_profile(self):
        self._auth()
        res = self.client.patch("/api/accounts/farmer/profile/", {
            "farm_name": "Моя ферма",
            "address": "Бишкек",
            "lat": 42.87,
            "lon": 74.59,
        })
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["farm_name"], "Моя ферма")


class ChangeRoleAPITest(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.user = make_user(email="role@test.com")

    def _auth(self):
        res = self.client.post("/api/accounts/login/", {
            "email": "role@test.com", "password": "pass1234"
        })
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {res.data['access']}")

    def test_change_to_farmer(self):
        self._auth()
        res = self.client.patch("/api/accounts/change-role/", {"role": "farmer"})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["role"], "farmer")
        self.user.refresh_from_db()
        self.assertTrue(FarmerProfile.objects.filter(user=self.user).exists())

    def test_change_to_invalid_role(self):
        self._auth()
        res = self.client.patch("/api/accounts/change-role/", {"role": "superadmin"})
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)