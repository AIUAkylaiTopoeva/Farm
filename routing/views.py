from typing import Dict, List, Optional

from django.db.models import Prefetch
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from market.models import Product
from accounts.models import FarmerProfile
from .serializers import (
    OptimizeRouteRequestSerializer,
    OptimizeRouteResponseSerializer,
)
from .utils import nearest_neighbor, route_length_km, group_products_by_farmer


class OptimizeRouteView(APIView):
    """
    POST /api/routing/optimize/
    body:
    {
      "product_ids": [1,2,3],
      "start": {"lat": 42.87, "lon": 74.59}   # optional
    }
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        req_ser = OptimizeRouteRequestSerializer(data=request.data)
        req_ser.is_valid(raise_exception=True)
        product_ids: List[int] = req_ser.validated_data["product_ids"]
        start: Optional[Dict] = req_ser.validated_data.get("start")

        # 1) Получаем продукты + владельцев
        products = (
            Product.objects
            .select_related("owner")
            .filter(id__in=product_ids, is_active=True)
        )

        found_ids = set(products.values_list("id", flat=True))
        missing = [pid for pid in product_ids if pid not in found_ids]
        if missing:
            return Response(
                {"detail": "Some product_ids not found or inactive", "missing_product_ids": missing},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # 2) Собираем "фармер-точки" из продуктов
        #    Одна ферма может иметь несколько выбранных продуктов — объединим.
        raw_points: List[Dict] = []
        owner_ids = set()

        for p in products:
            owner_ids.add(p.owner_id)
            raw_points.append({"farmer_id": p.owner_id, "product_id": p.id})

        products_by_farmer = group_products_by_farmer(raw_points)

        # 3) Достаём FarmerProfile для фермеров (координаты)
        profiles = FarmerProfile.objects.select_related("user").filter(user_id__in=owner_ids)
        profiles_map: Dict[int, FarmerProfile] = {fp.user_id: fp for fp in profiles}

        # 4) Формируем список точек только для фермеров, у которых есть lat/lon
        points: List[Dict] = []
        missing_coords = []

        for farmer_id, pids in products_by_farmer.items():
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
            return Response(
                {
                    "detail": "Some farmers have no coordinates (lat/lon) in FarmerProfile",
                    "farmer_ids_without_coords": missing_coords,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if len(points) < 2:
            return Response(
                {"detail": "Need at least 2 distinct farmers with coordinates to optimize route", "points": points},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # 5) Naive порядок: как получился список points (по порядку product_ids)
        # Стабилизируем naive: по порядку появления farmer_id в product_ids
        ordered_farmer_ids = []
        seen = set()
        for pid in product_ids:
            owner_id = Product.objects.filter(id=pid).values_list("owner_id", flat=True).first()
            if owner_id and owner_id not in seen and owner_id in products_by_farmer:
                ordered_farmer_ids.append(int(owner_id))
                seen.add(int(owner_id))

        points_map = {p["farmer_id"]: p for p in points}
        naive_points = [points_map[fid] for fid in ordered_farmer_ids if fid in points_map]

        # 6) Оптимизация (nearest neighbor)
        optimized_points = nearest_neighbor(naive_points, start=start)

        naive_distance = route_length_km(naive_points, start=start)
        optimized_distance = route_length_km(optimized_points, start=start)

        resp_data = {
            "naive_order_farmer_ids": [p["farmer_id"] for p in naive_points],
            "optimized_order_farmer_ids": [p["farmer_id"] for p in optimized_points],
            "naive_distance_km": round(naive_distance, 3),
            "optimized_distance_km": round(optimized_distance, 3),
            "points": optimized_points,
        }

        resp_ser = OptimizeRouteResponseSerializer(data=resp_data)
        resp_ser.is_valid(raise_exception=True)
        return Response(resp_ser.data, status=status.HTTP_200_OK)