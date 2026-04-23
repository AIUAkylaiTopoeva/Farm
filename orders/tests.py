from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from django.contrib.auth import get_user_model
from accounts.models import FarmerProfile
from market.models import Category, Product
from orders.models import Order, OrderItem, Review, Like

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


def make_product(owner, title="Морковь", price=100):
    cat, _ = Category.objects.get_or_create(name="Овощи")
    return Product.objects.create(
        owner=owner, category=cat,
        title=title, price=price
    )


ORDER_PAYLOAD = {
    "delivery_name": "Айгуль",
    "delivery_phone": "+996700123456",
    "delivery_address": "ул. Манаса 1",
    "delivery_city": "Бишкек",
}


class OrderCreateTest(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.customer = make_user(email="cust@test.com")
        self.farmer = make_farmer(email="farm@test.com")
        self.product = make_product(self.farmer)

    def _auth(self, email):
        token = get_token(self.client, email)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    def test_customer_can_create_order(self):
        self._auth("cust@test.com")
        payload = {
            **ORDER_PAYLOAD,
            "items": [{"product": self.product.id, "quantity": 2}]
        }
        res = self.client.post("/api/orders/create/", payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        order = Order.objects.get(id=res.data["id"])
        self.assertEqual(order.customer, self.customer)
        self.assertEqual(order.items.count(), 1)
        self.assertEqual(order.total_price, self.product.price * 2)

    def test_farmer_cannot_create_order(self):
        self._auth("farm@test.com")
        payload = {
            **ORDER_PAYLOAD,
            "items": [{"product": self.product.id, "quantity": 1}]
        }
        res = self.client.post("/api/orders/create/", payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_unauthenticated_cannot_create_order(self):
        payload = {
            **ORDER_PAYLOAD,
            "items": [{"product": self.product.id, "quantity": 1}]
        }
        res = self.client.post("/api/orders/create/", payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_order_with_empty_items_fails(self):
        self._auth("cust@test.com")
        payload = {**ORDER_PAYLOAD, "items": []}
        res = self.client.post("/api/orders/create/", payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_phone_fails(self):
        self._auth("cust@test.com")
        payload = {
            **ORDER_PAYLOAD,
            "delivery_phone": "123",
            "items": [{"product": self.product.id, "quantity": 1}]
        }
        res = self.client.post("/api/orders/create/", payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)


class OrderListTest(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.customer = make_user(email="cust@test.com")
        self.farmer = make_farmer(email="farm@test.com")
        self.product = make_product(self.farmer)

        # Создаём заказ вручную
        order = Order.objects.create(
            customer=self.customer,
            delivery_name="Айгуль",
            delivery_phone="+996700123456",
            delivery_address="ул. Манаса 1",
            delivery_city="Бишкек",
        )
        OrderItem.objects.create(
            order=order, product=self.product,
            quantity=1, price_at_order=self.product.price
        )
        order.calculate_total()

    def _auth(self, email):
        token = get_token(self.client, email)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    def test_customer_sees_own_orders(self):
        self._auth("cust@test.com")
        res = self.client.get("/api/orders/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(res.data), 1)

    def test_farmer_sees_orders_with_his_products(self):
        self._auth("farm@test.com")
        res = self.client.get("/api/orders/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(res.data), 1)


class OrderStatusUpdateTest(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.customer = make_user(email="cust@test.com")
        self.farmer = make_farmer(email="farm@test.com")
        self.product = make_product(self.farmer)

        self.order = Order.objects.create(
            customer=self.customer,
            delivery_name="Айгуль",
            delivery_phone="+996700123456",
            delivery_address="ул. Манаса 1",
            delivery_city="Бишкек",
        )
        OrderItem.objects.create(
            order=self.order, product=self.product,
            quantity=1, price_at_order=self.product.price
        )

    def _auth(self, email):
        token = get_token(self.client, email)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    def test_farmer_can_update_status(self):
        self._auth("farm@test.com")
        res = self.client.patch(
            f"/api/orders/{self.order.id}/status/",
            {"status": "confirmed"}
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, "confirmed")

    def test_customer_cannot_update_status(self):
        self._auth("cust@test.com")
        res = self.client.patch(
            f"/api/orders/{self.order.id}/status/",
            {"status": "confirmed"}
        )
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_invalid_status_rejected(self):
        self._auth("farm@test.com")
        res = self.client.patch(
            f"/api/orders/{self.order.id}/status/",
            {"status": "hacked"}
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)


class ReviewTest(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.customer = make_user(email="cust@test.com")
        self.farmer = make_farmer(email="farm@test.com")
        self.product = make_product(self.farmer)
        self.url = f"/api/products/{self.product.id}/reviews/"

    def _auth(self, email):
        token = get_token(self.client, email)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    def test_list_reviews_public(self):
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_customer_can_leave_review(self):
        self._auth("cust@test.com")
        res = self.client.post(self.url, {"rating": 5, "text": "Отлично!"})
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

    def test_farmer_cannot_review_own_product(self):
        self._auth("farm@test.com")
        res = self.client.post(self.url, {"rating": 5, "text": "Сам себе хвалю"})
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_duplicate_review_rejected(self):
        self._auth("cust@test.com")
        self.client.post(self.url, {"rating": 5, "text": "Первый"})
        res = self.client.post(self.url, {"rating": 4, "text": "Второй"})
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_delete_own_review(self):
        self._auth("cust@test.com")
        res = self.client.post(self.url, {"rating": 5, "text": "Отлично!"})
        review_id = res.data["id"]
        del_res = self.client.delete(f"/api/reviews/{review_id}/")
        self.assertEqual(del_res.status_code, status.HTTP_204_NO_CONTENT)


class LikeTest(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.customer = make_user(email="cust@test.com")
        self.farmer = make_farmer(email="farm@test.com")
        self.product = make_product(self.farmer)
        self.like_url = f"/api/products/{self.product.id}/like/"
        self.likes_url = f"/api/products/{self.product.id}/likes/"

    def _auth(self, email):
        token = get_token(self.client, email)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    def test_like_product(self):
        self._auth("cust@test.com")
        res = self.client.post(self.like_url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertTrue(res.data["liked"])
        self.assertEqual(res.data["likes_count"], 1)

    def test_unlike_product(self):
        self._auth("cust@test.com")
        self.client.post(self.like_url)  # лайк
        res = self.client.post(self.like_url)  # анлайк
        self.assertFalse(res.data["liked"])
        self.assertEqual(res.data["likes_count"], 0)

    def test_get_likes_count_public(self):
        res = self.client.get(self.likes_url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("likes_count", res.data)

    def test_unauthenticated_cannot_like(self):
        res = self.client.post(self.like_url)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)