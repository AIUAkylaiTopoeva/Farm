"""
Утилиты для оптимизации маршрута между фермами.
"""
import math
import urllib.request
import json
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


def get_real_distance(lat1, lon1, lat2, lon2):
    """OSRM → реальное расстояние. Fallback: Haversine × 1.3"""
    try:
        url = f"http://router.project-osrm.org/route/v1/driving/{lon1},{lat1};{lon2},{lat2}?overview=false"
        req = urllib.request.Request(url, headers={"User-Agent": "AgroPathKG/1.0"})
        with urllib.request.urlopen(req, timeout=3) as resp:
            data = json.loads(resp.read())
        if data.get("code") == "Ok":
            route = data["routes"][0]
            return {
                "distance_km": round(route["distance"] / 1000, 2),
                "duration_min": round(route["duration"] / 60, 1),
                "source": "osrm"
            }
    except Exception:
        pass
    dist = haversine_km(lat1, lon1, lat2, lon2) * 1.3
    return {
        "distance_km": round(dist, 2),
        "duration_min": round(dist / 40 * 60, 1),
        "source": "haversine"
    }


def group_products_by_farmer(raw_points: List[Dict]) -> Dict[int, List[int]]:
    result: Dict[int, List[int]] = {}
    for item in raw_points:
        fid = item["farmer_id"]
        pid = item["product_id"]
        if fid not in result:
            result[fid] = []
        if pid not in result[fid]:
            result[fid].append(pid)
    return result


def route_length_km(points: List[Dict], start: Optional[Dict] = None) -> float:
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


def nearest_neighbor(points: List[Dict], start: Optional[Dict] = None) -> List[Dict]:
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