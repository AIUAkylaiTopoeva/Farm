from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from django.contrib.auth import get_user_model
from accounts.models import FarmerProfile
from market.models import Category, Product
import io
from PIL import Image

User = get_user_model()


def make_user(email="u@test.com", password="pass1234", role="customer", verified=True):
    user = User.objects.create_user(email=email, password=password, role=role)
    if verified:
        user.is_active = True
        user.is_verified = True
        user.save(update_fields=["is_active", "is_verified"])
    return user


def make_farmer(email="farmer@test.com"):
    user = make_user(email=email, role="farmer")
    FarmerProfile.objects.get_or_create(user=user)
    return user


def get_token(client, email, password="pass1234"):
    res = client.post("/api/accounts/login/", {"email": email, "password": password})
    return res.data["access"]


def make_category(name="Овощи"):
    return Category.objects.create(name=name)


def make_product(owner, category, title="Морковь", price=100):
    return Product.objects.create(
        owner=owner, category=category,
        title=title, price=price
    )


def make_image_file(name="test.jpg"):
    """
    Создаёт изображение в памяти — без временных файлов.
    Работает на Windows без PermissionError.
    """
    buf = io.BytesIO()
    img = Image.new('RGB', (100, 100), color=(34, 139, 34))
    img.save(buf, format='JPEG')
    buf.seek(0)
    buf.name = name
    return buf


class CategoryModelTest(TestCase):

    def test_slug_auto_generated(self):
        cat = make_category("Свежие Овощи")
        self.assertTrue(cat.slug)
        self.assertNotIn(" ", cat.slug)

    def test_slug_unique_on_duplicate_name(self):
        c1 = Category.objects.create(name="Фрукты разные")
        c2 = Category.objects.create(name="Фрукты свежие")
        self.assertNotEqual(c1.slug, c2.slug)


class CategoryAPITest(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.admin = make_user(email="admin@test.com", role="admin")
        self.admin.is_staff = True
        self.admin.save()
        self.cat = make_category()

    def _auth(self, user_email, password="pass1234"):
        token = get_token(self.client, user_email, password)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    def test_list_categories_public(self):
        res = self.client.get("/api/categories/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_create_category_as_admin(self):
        self._auth("admin@test.com")
        res = self.client.post("/api/categories/", {"name": "Зелень"})
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

    def test_create_category_as_customer_forbidden(self):
        make_user(email="cust@test.com")
        self._auth("cust@test.com")
        res = self.client.post("/api/categories/", {"name": "Зелень"})
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class ProductAPITest(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.farmer = make_farmer(email="farm@test.com")
        self.customer = make_user(email="cust@test.com")
        self.category = make_category()
        self.product = make_product(self.farmer, self.category)

    def _auth(self, email, password="pass1234"):
        token = get_token(self.client, email, password)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    def test_list_products_public(self):
        res = self.client.get("/api/products/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_retrieve_product_public(self):
        res = self.client.get(f"/api/products/{self.product.id}/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["title"], "Морковь")

    def test_create_product_as_farmer(self):
        self._auth("farm@test.com")
        res = self.client.post("/api/products/", {
            "category": self.category.id,
            "title": "Картошка",
            "price": "50.00",
            "weight_kg": "1.0",
            "image": make_image_file(),  # ← в памяти, без файла
        }, format="multipart")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data["owner_email"], "farm@test.com")

    def test_create_product_as_customer_forbidden(self):
        self._auth("cust@test.com")
        res = self.client.post("/api/products/", {
            "category": self.category.id,
            "title": "Картошка",
            "price": "50.00",
            "image": make_image_file(),
        }, format="multipart")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_update_product_as_owner(self):
        self._auth("farm@test.com")
        res = self.client.patch(
            f"/api/products/{self.product.id}/",
            {"price": "200.00"},
            format="multipart"
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_delete_product_as_owner(self):
        self._auth("farm@test.com")
        res = self.client.delete(f"/api/products/{self.product.id}/")
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)

    def test_delete_product_as_other_farmer_forbidden(self):
        make_farmer(email="other@test.com")
        self._auth("other@test.com")
        res = self.client.delete(f"/api/products/{self.product.id}/")
        self.assertIn(res.status_code, [
            status.HTTP_403_FORBIDDEN,
            status.HTTP_404_NOT_FOUND,
        ])

    def test_filter_by_category(self):
        res = self.client.get(f"/api/products/?category={self.category.slug}")
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_filter_by_price_range(self):
        res = self.client.get("/api/products/?min_price=50&max_price=200")
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_search_by_title(self):
        res = self.client.get("/api/products/?search=Морковь")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        # Работает и с пагинацией и без
        data = res.data
        if isinstance(data, dict) and "results" in data:
            self.assertGreaterEqual(len(data["results"]), 1)
        else:
            self.assertGreaterEqual(len(data), 1)