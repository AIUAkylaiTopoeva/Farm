"""
routing/views.py
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
from .utils import (
    nearest_neighbor, route_length_km,
    group_products_by_farmer, get_route_geometry,
)
from .scorer import compare_route_profiles


def _resolve_points(product_ids: List[int]) -> tuple:
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

    raw_points = [{"farmer_id": p.owner_id, "product_id": p.id} for p in products]
    products_by_farmer = group_products_by_farmer(raw_points)

    order_map: Dict[int, int] = {}
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


class OptimizeRouteView(APIView):
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
            fuel_price=fuel_price,
            fuel_consumption=fuel_consumption,
        )

        comparison["points"] = nearest_neighbor(points, start=start)

        # ── Геометрия реального маршрута по дорогам ──────────────────────
        # Берём balanced маршрут и строим геометрию через OSRM
        best_route = comparison.get("profile_routes", {}).get("balanced", [])
        geometry = []

        all_points = []
        if start:
            all_points.append({"lat": start["lat"], "lon": start["lon"]})
        all_points.extend(best_route)

        for i in range(len(all_points) - 1):
            segment = get_route_geometry(
                all_points[i]["lat"], all_points[i]["lon"],
                all_points[i + 1]["lat"], all_points[i + 1]["lon"],
            )
            if segment:
                # Избегаем дублирования точек на стыках сегментов
                if geometry and segment:
                    geometry.extend(segment[1:])
                else:
                    geometry.extend(segment)

        comparison["route_geometry"] = geometry
        # ─────────────────────────────────────────────────────────────────

        return Response(comparison, status=status.HTTP_200_OK)