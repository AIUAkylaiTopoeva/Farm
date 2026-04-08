"""
Многокритериальная оценка маршрута для диплома AgroPath KG.
Целевая функция (минимизируем):
    F(route) = w1·D + w2·C + w3·T + w4·R
Где:
    D — расстояние (км)
    C — стоимость топлива (сом)
    T — время в пути (минуты)
    R — штраф за качество дороги (безразмерный)
    w1..w4 — веса критериев (задаются пользователем или по умолчанию)
Три профиля оптимизации:
    "cheapest"   — минимум денег  (w2 большой)
    "fastest"    — минимум времени (w3 большой)
    "balanced"   — всё поровну
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .utils import haversine_km, route_length_km, nearest_neighbor

# ── Константы (Бишкек, 2025) ───────────────────────────────────────────────

FUEL_PRICE_SOM = 55.0           # сом за литр АИ-92
FUEL_L_PER_100KM = 8.0          # расход литров на 100 км (средний авто)
AVG_SPEED_KMH = 40.0            # средняя скорость (город + область)
ROAD_FACTOR = 1.3               # Haversine → реальная дорога (поправка)

ROAD_QUALITY_FACTORS = {
    "good":   1.0,   # асфальт
    "medium": 1.2,   # частично разбитый
    "bad":    1.5,   # грунтовка / горная дорога
}

# Профили весов [w1_dist, w2_cost, w3_time, w4_road]
WEIGHT_PROFILES = {
    "cheapest":  {"w1": 0.1, "w2": 0.6, "w3": 0.2, "w4": 0.1},
    "fastest":   {"w1": 0.2, "w2": 0.1, "w3": 0.6, "w4": 0.1},
    "balanced":  {"w1": 0.25, "w2": 0.25, "w3": 0.25, "w4": 0.25},
}


# ── Расчёт показателей одного маршрута ────────────────────────────────────

def score_route(
    points: List[Dict],
    start: Optional[Dict] = None,
    road_quality: str = "medium",
    weights: Optional[Dict[str, float]] = None,
) -> Dict:
    """
    Считает все показатели для одного маршрута и итоговый score F(route).

    Параметры:
        points       — список точек маршрута [{"lat", "lon", ...}]
        start        — стартовая точка покупателя {"lat", "lon"} (опционально)
        road_quality — "good" / "medium" / "bad"
        weights      — {"w1", "w2", "w3", "w4"} или None (используется balanced)

    Возвращает dict со всеми показателями + итоговым score.
    """
    if weights is None:
        weights = WEIGHT_PROFILES["balanced"]

    road_factor = ROAD_QUALITY_FACTORS.get(road_quality, 1.3)

    # D — реальное расстояние (Haversine × поправка)
    straight_km = route_length_km(points, start=start)
    distance_km = straight_km * road_factor

    # C — стоимость топлива
    fuel_used_l = (distance_km / 100) * FUEL_L_PER_100KM
    fuel_cost_som = fuel_used_l * FUEL_PRICE_SOM

    # T — время в пути (минуты)
    travel_time_min = (distance_km / AVG_SPEED_KMH) * 60

    # R — штраф за качество дороги
    road_penalty = road_factor  # 1.0 / 1.2 / 1.5

    # Нормализуем компоненты к одному масштабу (делим на типичные значения)
    # чтобы веса имели смысл
    D_norm = distance_km / 50.0          # типичный маршрут ~50 км
    C_norm = fuel_cost_som / 200.0       # типичная стоимость ~200 сом
    T_norm = travel_time_min / 60.0      # типичное время ~60 минут
    R_norm = (road_penalty - 1.0) / 0.5  # 0..1 диапазон

    score = (
        weights["w1"] * D_norm +
        weights["w2"] * C_norm +
        weights["w3"] * T_norm +
        weights["w4"] * R_norm
    )

    return {
        "distance_km":      round(distance_km, 2),
        "fuel_used_l":      round(fuel_used_l, 2),
        "fuel_cost_som":    round(fuel_cost_som, 2),
        "travel_time_min":  round(travel_time_min, 1),
        "road_quality":     road_quality,
        "road_penalty":     road_penalty,
        "score":            round(score, 4),   # меньше = лучше
    }


# ── Сравнение трёх профилей ────────────────────────────────────────────────

def compare_route_profiles(
    points: List[Dict],
    start: Optional[Dict] = None,
    road_quality: str = "medium",
) -> Dict:
    """
    Считает маршрут по трём профилям и определяет победителя каждого.
    Возвращает готовый ответ для Flutter с экономией.

    Структура ответа:
    {
      "profiles": {
        "cheapest":  {...показатели...},
        "fastest":   {...},
        "balanced":  {...},
      },
      "winner": {
        "cheapest":  "cheapest",   # самый дешёвый профиль по cost
        "fastest":   "fastest",    # самый быстрый по времени
        "best_score":"balanced",   # лучший общий score
      },
      "savings": {
        "money_som":  120.5,   # экономия денег vs худшего варианта
        "time_min":   18.0,    # экономия времени vs худшего варианта
        "distance_km": 7.4,
      }
    }
    """
    results = {}
    for profile_name, weights in WEIGHT_PROFILES.items():
        # Для каждого профиля пересортируем точки nearest_neighbor
        # с учётом профиля (в текущей реализации порядок одинаков,
        # но структура готова для расширения с разными алгоритмами)
        optimized_points = nearest_neighbor(points, start=start)
        results[profile_name] = score_route(
            optimized_points,
            start=start,
            road_quality=road_quality,
            weights=weights,
        )

    # Определяем победителей
    cheapest_profile = min(results, key=lambda k: results[k]["fuel_cost_som"])
    fastest_profile  = min(results, key=lambda k: results[k]["travel_time_min"])
    best_score       = min(results, key=lambda k: results[k]["score"])

    # Считаем экономию (разница между лучшим и худшим вариантом)
    all_costs  = [r["fuel_cost_som"]   for r in results.values()]
    all_times  = [r["travel_time_min"] for r in results.values()]
    all_dists  = [r["distance_km"]     for r in results.values()]

    savings = {
        "money_som":   round(max(all_costs) - min(all_costs), 2),
        "time_min":    round(max(all_times) - min(all_times), 1),
        "distance_km": round(max(all_dists) - min(all_dists), 2),
    }

    return {
        "profiles": results,
        "winner": {
            "cheapest":   cheapest_profile,
            "fastest":    fastest_profile,
            "best_score": best_score,
        },
        "savings": savings,
    }