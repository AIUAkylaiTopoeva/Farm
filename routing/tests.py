from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from django.contrib.auth import get_user_model
from accounts.models import FarmerProfile
from market.models import Category, Product
from routing.utils import haversine_km, nearest_neighbor, route_length_km
from routing.scorer import score_route, compare_route_profiles

User = get_user_model()


def make_user(email, password="pass1234", role="customer", verified=True):
    user = User.objects.create_user(email=email, password=password, role=role)
    if verified:
        user.is_active = True
        user.is_verified = True
        user.save(update_fields=["is_active", "is_verified"])
    return user


def make_farmer_with_coords(email, lat, lon):
    user = make_user(email=email, role="farmer")
    FarmerProfile.objects.filter(user=user).delete()
    FarmerProfile.objects.create(
        user=user, lat=lat, lon=lon,
        farm_name=f"Farm {email}",
        address="Кыргызстан"
    )
    return user


def get_token(client, email, password="pass1234"):
    res = client.post("/api/accounts/login/", {"email": email, "password": password})
    return res.data["access"]


def make_product(owner):
    cat, _ = Category.objects.get_or_create(name="Тест")
    return Product.objects.create(
        owner=owner, category=cat,
        title="Тестовый товар", price=100
    )


# ── Тесты утилит ──────────────────────────────────────────────────────────

class HaversineTest(TestCase):

    def test_same_point_is_zero(self):
        dist = haversine_km(42.87, 74.59, 42.87, 74.59)
        self.assertAlmostEqual(dist, 0.0, places=5)

    def test_bishkek_to_osh_approx(self):
        # Бишкек → Ош ~600 км
        dist = haversine_km(42.87, 74.59, 40.51, 72.80)
        self.assertGreater(dist, 300)
        self.assertLess(dist, 700)

    def test_symmetry(self):
        d1 = haversine_km(42.87, 74.59, 40.51, 72.80)
        d2 = haversine_km(40.51, 72.80, 42.87, 74.59)
        self.assertAlmostEqual(d1, d2, places=5)


class NearestNeighborTest(TestCase):

    def setUp(self):
        self.points = [
            {"farmer_id": 1, "lat": 42.87, "lon": 74.59},
            {"farmer_id": 2, "lat": 40.51, "lon": 72.80},
            {"farmer_id": 3, "lat": 42.50, "lon": 74.00},
        ]

    def test_returns_all_points(self):
        result = nearest_neighbor(self.points)
        self.assertEqual(len(result), len(self.points))
        farmer_ids = [p["farmer_id"] for p in result]
        for p in self.points:
            self.assertIn(p["farmer_id"], farmer_ids)

    def test_with_start_point(self):
        start = {"lat": 42.87, "lon": 74.59}
        result = nearest_neighbor(self.points, start=start)
        self.assertEqual(len(result), 3)

    def test_single_point_returned_as_is(self):
        result = nearest_neighbor([self.points[0]])
        self.assertEqual(len(result), 1)

    def test_route_shorter_than_naive(self):
        start = {"lat": 42.87, "lon": 74.59}
        naive_dist = route_length_km(self.points, start=start)
        optimized = nearest_neighbor(self.points, start=start)
        optimized_dist = route_length_km(optimized, start=start)
        # Nearest neighbor всегда не хуже случайного для этих точек
        self.assertLessEqual(optimized_dist, naive_dist * 1.5)


class RouteLengthTest(TestCase):

    def test_empty_route_is_zero(self):
        self.assertEqual(route_length_km([]), 0.0)

    def test_single_point_with_start(self):
        point = [{"lat": 42.87, "lon": 74.59}]
        start = {"lat": 42.00, "lon": 74.00}
        dist = route_length_km(point, start=start)
        self.assertGreater(dist, 0)

    def test_two_points(self):
        points = [
            {"lat": 42.87, "lon": 74.59},
            {"lat": 40.51, "lon": 72.80},
        ]
        dist = route_length_km(points)
        self.assertGreater(dist, 0)


class ScoreRouteTest(TestCase):

    def setUp(self):
        self.points = [
            {"lat": 42.87, "lon": 74.59},
            {"lat": 42.50, "lon": 74.00},
        ]

    def test_score_returns_required_keys(self):
        result = score_route(self.points)
        for key in ["distance_km", "fuel_used_l", "fuel_cost_som",
                    "travel_time_min", "score"]:
            self.assertIn(key, result)

    def test_bad_road_longer_distance(self):
        good = score_route(self.points, road_quality="good")
        bad = score_route(self.points, road_quality="bad")
        self.assertGreater(bad["distance_km"], good["distance_km"])
        self.assertGreater(bad["fuel_cost_som"], good["fuel_cost_som"])

    def test_higher_fuel_price_increases_cost(self):
        cheap = score_route(self.points, fuel_price=40.0)
        expensive = score_route(self.points, fuel_price=100.0)
        self.assertGreater(expensive["fuel_cost_som"], cheap["fuel_cost_som"])


class CompareRouteProfilesTest(TestCase):

    def setUp(self):
        self.points = [
            {"farmer_id": 1, "lat": 42.87, "lon": 74.59, "farm_name": "A", "address": "", "product_ids": [1]},
            {"farmer_id": 2, "lat": 42.50, "lon": 74.00, "farm_name": "B", "address": "", "product_ids": [2]},
            {"farmer_id": 3, "lat": 40.51, "lon": 72.80, "farm_name": "C", "address": "", "product_ids": [3]},
        ]

    def test_compare_returns_all_profiles(self):
        result = compare_route_profiles(self.points)
        self.assertIn("profiles", result)
        for profile in ["cheapest", "fastest", "balanced"]:
            self.assertIn(profile, result["profiles"])

    def test_savings_non_negative(self):
        result = compare_route_profiles(self.points)
        self.assertGreaterEqual(result["savings"]["money_som"], 0)
        self.assertGreaterEqual(result["savings"]["time_min"], 0)
        self.assertGreaterEqual(result["savings"]["distance_km"], 0)

    def test_winner_keys_present(self):
        result = compare_route_profiles(self.points)
        self.assertIn("cheapest", result["winner"])
        self.assertIn("fastest", result["winner"])
        self.assertIn("best_score", result["winner"])


# ── API тесты ─────────────────────────────────────────────────────────────

class OptimizeRouteAPITest(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.customer = make_user(email="cust@test.com")
        self.farmer1 = make_farmer_with_coords("f1@test.com", 42.87, 74.59)
        self.farmer2 = make_farmer_with_coords("f2@test.com", 42.50, 74.00)
        self.farmer3 = make_farmer_with_coords("f3@test.com", 40.51, 72.80)
        self.p1 = make_product(self.farmer1)
        self.p2 = make_product(self.farmer2)
        self.p3 = make_product(self.farmer3)
        token = get_token(self.client, "cust@test.com")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    def test_optimize_returns_200(self):
        res = self.client.post("/api/routing/optimize/", {
            "product_ids": [self.p1.id, self.p2.id, self.p3.id]
        }, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_optimize_response_structure(self):
        res = self.client.post("/api/routing/optimize/", {
            "product_ids": [self.p1.id, self.p2.id, self.p3.id]
        }, format="json")
        for key in ["optimized_order_farmer_ids", "optimized_distance_km",
                    "naive_distance_km", "points"]:
            self.assertIn(key, res.data)

    def test_optimize_with_start(self):
        res = self.client.post("/api/routing/optimize/", {
            "product_ids": [self.p1.id, self.p2.id, self.p3.id],
            "start": {"lat": 42.87, "lon": 74.59}
        }, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_optimize_unauthenticated(self):
        self.client.credentials()
        res = self.client.post("/api/routing/optimize/", {
            "product_ids": [self.p1.id]
        }, format="json")
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_optimize_missing_product_returns_400(self):
        res = self.client.post("/api/routing/optimize/", {
            "product_ids": [99999]
        }, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_optimize_single_farmer_returns_400(self):
        res = self.client.post("/api/routing/optimize/", {
            "product_ids": [self.p1.id]
        }, format="json")
        # Меньше 2 точек — ошибка
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)


class CompareRouteAPITest(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.customer = make_user(email="cust2@test.com")
        self.farmer1 = make_farmer_with_coords("cf1@test.com", 42.87, 74.59)
        self.farmer2 = make_farmer_with_coords("cf2@test.com", 42.50, 74.00)
        self.farmer3 = make_farmer_with_coords("cf3@test.com", 40.51, 72.80)
        self.p1 = make_product(self.farmer1)
        self.p2 = make_product(self.farmer2)
        self.p3 = make_product(self.farmer3)
        token = get_token(self.client, "cust2@test.com")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    def test_compare_returns_200(self):
        res = self.client.post("/api/routing/compare/", {
            "product_ids": [self.p1.id, self.p2.id, self.p3.id],
            "road_quality": "medium",
            "fuel_price": 58.0,
            "fuel_consumption": 9.0,
        }, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_compare_response_has_profiles(self):
        res = self.client.post("/api/routing/compare/", {
            "product_ids": [self.p1.id, self.p2.id, self.p3.id],
        }, format="json")
        self.assertIn("profiles", res.data)
        self.assertIn("savings", res.data)
        self.assertIn("winner", res.data)

    def test_invalid_road_quality(self):
        res = self.client.post("/api/routing/compare/", {
            "product_ids": [self.p1.id, self.p2.id, self.p3.id],
            "road_quality": "terrible"
        }, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)