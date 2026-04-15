"""
routing/views.py

POST /api/routing/optimize/   — оптимизация порядка ферм (nearest neighbor)
POST /api/routing/compare/    — многокритериальное сравнение маршрутов
                                (cheapest / fastest / balanced)
"""

from typing import Dict, List, Optional

from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from market.models import Product
from accounts.models import FarmerProfile
from .serializers import (
    OptimizeRouteRequestSerializer,
    OptimizeRouteResponseSerializer,
    CompareRouteRequestSerializer,
)
from .utils import nearest_neighbor, route_length_km, group_products_by_farmer
from .scorer import compare_route_profiles



def _resolve_points(product_ids: List[int]) -> tuple:
    """
    По списку product_ids возвращает (points, error_response или None).
    points — список dict с координатами ферм.
    Исправлен N+1 запрос: используем один словарь вместо цикла с ORM.
    """
    products = (
        Product.objects
        .select_related("owner")
        .filter(id__in=product_ids, is_active=True)
    )

    found_ids = set(products.values_list("id", flat=True))
    missing = [pid for pid in product_ids if pid not in found_ids]
    if missing:
        return None, {
            "detail": "Some product_ids not found or inactive",
            "missing_product_ids": missing,
        }

    # Группируем товары по фермеру (без N+1)
    raw_points = [{"farmer_id": p.owner_id, "product_id": p.id} for p in products]
    products_by_farmer = group_products_by_farmer(raw_points)

    # Строим словарь owner_id → порядок появления (по product_ids)
    order_map: Dict[int, int] = {}
    # Один запрос вместо цикла
    pid_to_owner = {p.id: p.owner_id for p in products}
    for pid in product_ids:
        owner_id = pid_to_owner.get(pid)
        if owner_id and owner_id not in order_map:
            order_map[owner_id] = len(order_map)

    owner_ids = set(products_by_farmer.keys())
    profiles = FarmerProfile.objects.select_related("user").filter(user_id__in=owner_ids)
    profiles_map: Dict[int, FarmerProfile] = {fp.user_id: fp for fp in profiles}

    points: List[Dict] = []
    missing_coords = []

    # Сортируем по порядку появления в запросе
    for farmer_id in sorted(products_by_farmer.keys(), key=lambda fid: order_map.get(fid, 999)):
        pids = products_by_farmer[farmer_id]
        fp = profiles_map.get(farmer_id)
        if not fp or fp.lat is None or fp.lon is None:
            missing_coords.append(farmer_id)
            continue
        points.append({
            "farmer_id": farmer_id,
            "farm_name": fp.farm_name or "",
            "address": fp.address or "",
            "lat": float(fp.lat),
            "lon": float(fp.lon),
            "product_ids": pids,
        })

    if missing_coords:
        return None, {
            "detail": "Some farmers have no coordinates in FarmerProfile",
            "farmer_ids_without_coords": missing_coords,
        }

    if len(points) < 2:
        return None, {
            "detail": "Need at least 2 distinct farmers with coordinates",
            "points": points,
        }

    return points, None


# ── View 1: Оптимизация порядка ────────────────────────────────────────────

class OptimizeRouteView(APIView):
    """
    POST /api/routing/optimize/

    Принимает список product_ids, возвращает оптимальный порядок объезда ферм
    (алгоритм nearest neighbor) и сравнение с наивным порядком.

    Body:
    {
      "product_ids": [1, 2, 3],
      "start": {"lat": 42.87, "lon": 74.59}   // опционально
    }
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        req_ser = OptimizeRouteRequestSerializer(data=request.data)
        req_ser.is_valid(raise_exception=True)

        product_ids: List[int] = req_ser.validated_data["product_ids"]
        start: Optional[Dict] = req_ser.validated_data.get("start")

        points, error = _resolve_points(product_ids)
        if error:
            return Response(error, status=status.HTTP_400_BAD_REQUEST)

        naive_points = list(points)
        optimized_points = nearest_neighbor(points, start=start)

        naive_distance = route_length_km(naive_points, start=start)
        optimized_distance = route_length_km(optimized_points, start=start)

        resp_data = {
            "naive_order_farmer_ids":     [p["farmer_id"] for p in naive_points],
            "optimized_order_farmer_ids": [p["farmer_id"] for p in optimized_points],
            "naive_distance_km":      round(naive_distance, 3),
            "optimized_distance_km":  round(optimized_distance, 3),
            "points": optimized_points,
        }

        resp_ser = OptimizeRouteResponseSerializer(data=resp_data)
        resp_ser.is_valid(raise_exception=True)
        return Response(resp_ser.data, status=status.HTTP_200_OK)


# ── View 2: Многокритериальное сравнение ───────────────────────────────────

class CompareRouteView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        req_ser = CompareRouteRequestSerializer(data=request.data)
        req_ser.is_valid(raise_exception=True)

        product_ids = req_ser.validated_data["product_ids"]
        start = req_ser.validated_data.get("start")
        road_quality = req_ser.validated_data.get("road_quality", "medium")
        fuel_price = req_ser.validated_data.get("fuel_price", 55.0)
        fuel_consumption = req_ser.validated_data.get("fuel_consumption", 8.0)

        points, error = _resolve_points(product_ids)
        if error:
            return Response(error, status=status.HTTP_400_BAD_REQUEST)

        comparison = compare_route_profiles(
            points,
            start=start,
            road_quality=road_quality,
            fuel_price=req_ser.validated_data.get("fuel_price", 55.0),
            fuel_consumption=req_ser.validated_data.get("fuel_consumption", 8.0),
        )

        from .utils import nearest_neighbor as nn
        comparison["points"] = nn(points, start=start)

        return Response(comparison, status=status.HTTP_200_OK)