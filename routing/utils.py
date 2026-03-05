import math
from typing import Dict, List, Optional, Tuple


def haversine_km(a: Dict, b: Dict) -> float:
    """
    Расстояние между двумя точками на сфере (км).
    a/b: {"lat": float, "lon": float}
    """
    r = 6371.0
    lat1 = math.radians(float(a["lat"]))
    lon1 = math.radians(float(a["lon"]))
    lat2 = math.radians(float(b["lat"]))
    lon2 = math.radians(float(b["lon"]))

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    h = (math.sin(dlat / 2) ** 2) + math.cos(lat1) * math.cos(lat2) * (math.sin(dlon / 2) ** 2)
    return 2 * r * math.asin(math.sqrt(h))


def route_length_km(points: List[Dict], start: Optional[Dict] = None) -> float:
    """
    Длина маршрута: start -> points[0] -> ... -> points[n-1]
    (без возврата в начало).
    """
    if not points:
        return 0.0

    dist = 0.0
    prev = start if start else points[0]
    idx0 = 0 if start else 1  # если start отсутствует, начинаем с points[0] как "старт" и считаем со 2-й точки

    for i in range(idx0, len(points)):
        dist += haversine_km(prev, points[i])
        prev = points[i]
    return float(dist)


def nearest_neighbor(points: List[Dict], start: Optional[Dict] = None) -> List[Dict]:
    """
    Эвристика: каждый раз идём в ближайшую следующую точку.
    Возвращает новый список (не меняет исходный).
    """
    if not points:
        return []

    unvisited = points[:]
    route: List[Dict] = []

    current = start if start else unvisited.pop(0)
    if not start:
        # если start не задан, первая точка считается посещенной и в маршруте первой
        route.append(current)

    while unvisited:
        nxt = min(unvisited, key=lambda p: haversine_km(current, p))
        route.append(nxt)
        unvisited.remove(nxt)
        current = nxt

    return route


def group_products_by_farmer(points: List[Dict]) -> Dict[int, List[int]]:
    """
    points: элементы с farmer_id и product_id
    -> farmer_id: [product_ids]
    """
    res: Dict[int, List[int]] = {}
    for p in points:
        fid = int(p["farmer_id"])
        res.setdefault(fid, []).append(int(p["product_id"]))
    return res