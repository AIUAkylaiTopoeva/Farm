"""
Утилиты для оптимизации маршрута между фермами.
Точка вида: {"farmer_id": int, "lat": float, "lon": float, ...}
"""
import math
from typing import Dict, List, Optional

def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Расстояние между двумя GPS-точками по формуле Haversine (км)."""
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = (
        math.sin(dphi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    )
    return R * 2 * math.asin(math.sqrt(a))



def group_products_by_farmer(raw_points: List[Dict]) -> Dict[int, List[int]]:
    """
    Принимает список {"farmer_id": int, "product_id": int}.
    Возвращает {farmer_id: [product_id, ...]} сгруппированные по ферме.
    Порядок фермеров — по первому появлению в списке.
    """
    result: Dict[int, List[int]] = {}
    for item in raw_points:
        fid = item["farmer_id"]
        pid = item["product_id"]
        if fid not in result:
            result[fid] = []
        if pid not in result[fid]:
            result[fid].append(pid)
    return result


def route_length_km(
    points: List[Dict],
    start: Optional[Dict] = None,
) -> float:
    """
    Считает суммарную длину маршрута через все точки (км).
    Если передан start — добавляет расстояние от старта до первой точки.
    """
    if not points:
        return 0.0

    total = 0.0

    if start:
        total += haversine_km(
            start["lat"], start["lon"],
            points[0]["lat"], points[0]["lon"],
        )

    for i in range(len(points) - 1):
        total += haversine_km(
            points[i]["lat"], points[i]["lon"],
            points[i + 1]["lat"], points[i + 1]["lon"],
        )

    return total



def nearest_neighbor(
    points: List[Dict],
    start: Optional[Dict] = None,
) -> List[Dict]:
    """
    Жадный алгоритм ближайшего соседа (Nearest Neighbor).
    Каждый раз выбирает ближайшую ещё не посещённую точку.
    Возвращает переупорядоченный список точек.
    """
    if len(points) <= 1:
        return list(points)

    unvisited = list(points)
    route = []

    if start:
        current_lat = start["lat"]
        current_lon = start["lon"]
    else:
        first = unvisited.pop(0)
        route.append(first)
        current_lat = first["lat"]
        current_lon = first["lon"]

    while unvisited:
        nearest = min(
            unvisited,
            key=lambda p: haversine_km(current_lat, current_lon, p["lat"], p["lon"]),
        )
        route.append(nearest)
        unvisited.remove(nearest)
        current_lat = nearest["lat"]
        current_lon = nearest["lon"]

    return route