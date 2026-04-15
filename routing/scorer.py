"""
routing/scorer.py

Многокритериальная оценка маршрута для диплома AgroPath KG.

Целевая функция (минимизируем):
    F(route) = w1·D + w2·C + w3·T + w4·R

Где:
    D — расстояние (км)
    C — стоимость топлива (сом)
    T — время в пути (минуты)
    R — штраф за качество дороги (безразмерный)

Три профиля оптимизации:
    "cheapest" — минимум денег  (w2 большой)
    "fastest"  — минимум времени (w3 большой)
    "balanced" — всё поровну

Алгоритм: Google OR-Tools (TSP solver)
Fallback:  Nearest Neighbor если OR-Tools недоступен
"""

from typing import Dict, List, Optional
from .utils import route_length_km, nearest_neighbor, haversine_km

# ── Константы ─────────────────────────────────────────────────────────────

DEFAULT_FUEL_PRICE_SOM    = 55.0
DEFAULT_FUEL_L_PER_100KM  = 8.0
AVG_SPEED_KMH             = 40.0

ROAD_QUALITY_FACTORS = {
    "good":   1.0,
    "medium": 1.2,
    "bad":    1.5,
}

WEIGHT_PROFILES = {
    "cheapest": {"w1": 0.1,  "w2": 0.6,  "w3": 0.2,  "w4": 0.1},
    "fastest":  {"w1": 0.2,  "w2": 0.1,  "w3": 0.6,  "w4": 0.1},
    "balanced": {"w1": 0.25, "w2": 0.25, "w3": 0.25, "w4": 0.25},
}


# ── OR-Tools оптимизация ──────────────────────────────────────────────────

def _build_distance_matrix(
    points: List[Dict],
    start: Optional[Dict],
    road_quality: str,
    weight_distance: float,
    weight_time: float,
    fuel_price: float,
    fuel_consumption: float,
) -> List[List[int]]:
    """
    Строит матрицу стоимости перехода между точками.
    Стоимость = взвешенная комбинация расстояния и топлива.
    Умножаем на 1000 чтобы перевести в целые числа для OR-Tools.
    """
    road_factor = ROAD_QUALITY_FACTORS.get(road_quality, 1.2)
    all_points = []
    if start:
        all_points.append(start)
    all_points.extend(points)

    n = len(all_points)
    matrix = []

    for i in range(n):
        row = []
        for j in range(n):
            if i == j:
                row.append(0)
            else:
                dist_km = haversine_km(
                    all_points[i]["lat"], all_points[i]["lon"],
                    all_points[j]["lat"], all_points[j]["lon"],
                ) * road_factor

                fuel_cost = (dist_km / 100) * fuel_consumption * fuel_price
                time_min  = (dist_km / AVG_SPEED_KMH) * 60

                # Взвешенная стоимость перехода
                cost = weight_distance * dist_km + weight_time * time_min + fuel_cost
                row.append(int(cost * 1000))
        matrix.append(row)

    return matrix


def _solve_with_ortools(
    points: List[Dict],
    start: Optional[Dict],
    road_quality: str,
    weight_distance: float,
    weight_time: float,
    fuel_price: float,
    fuel_consumption: float,
) -> List[Dict]:
    """
    Решает задачу TSP через Google OR-Tools.
    Возвращает оптимальный порядок точек.
    Fallback на Nearest Neighbor если OR-Tools недоступен.
    """
    try:
        from ortools.constraint_solver import routing_enums_pb2
        from ortools.constraint_solver import pywrapcp
    except ImportError:
        # OR-Tools не установлен — используем Nearest Neighbor
        return nearest_neighbor(points, start=start)

    if len(points) <= 1:
        return list(points)

    matrix = _build_distance_matrix(
        points, start, road_quality,
        weight_distance, weight_time,
        fuel_price, fuel_consumption,
    )

    n = len(matrix)
    depot = 0  # стартовая точка — индекс 0

    manager = pywrapcp.RoutingIndexManager(n, 1, depot)
    routing = pywrapcp.RoutingModel(manager)

    def distance_callback(from_index, to_index):
        from_node = manager.IndexToNode(from_index)
        to_node   = manager.IndexToNode(to_index)
        return matrix[from_node][to_node]

    transit_callback_index = routing.RegisterTransitCallback(distance_callback)
    routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

    search_params = pywrapcp.DefaultRoutingSearchParameters()
    search_params.first_solution_strategy = (
        routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    )
    search_params.local_search_metaheuristic = (
        routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
    )
    search_params.time_limit.seconds = 2  # максимум 2 секунды

    solution = routing.SolveWithParameters(search_params)

    if not solution:
        # OR-Tools не нашёл решение — fallback
        return nearest_neighbor(points, start=start)

    # Извлекаем порядок ферм (пропускаем depot если есть start)
    order = []
    index = routing.Start(0)
    while not routing.IsEnd(index):
        node = manager.IndexToNode(index)
        if start:
            # node=0 это стартовая точка, пропускаем
            if node > 0:
                order.append(node - 1)
        else:
            order.append(node)
        index = solution.Value(routing.NextVar(index))

    return [points[i] for i in order if i < len(points)]


# ── Расчёт показателей одного маршрута ───────────────────────────────────

def score_route(
    points: List[Dict],
    start: Optional[Dict] = None,
    road_quality: str = "medium",
    weights: Optional[Dict[str, float]] = None,
    fuel_price: float = DEFAULT_FUEL_PRICE_SOM,
    fuel_consumption: float = DEFAULT_FUEL_L_PER_100KM,
) -> Dict:
    """
    Считает все показатели для одного маршрута и итоговый score F(route).
    """
    if weights is None:
        weights = WEIGHT_PROFILES["balanced"]

    road_factor = ROAD_QUALITY_FACTORS.get(road_quality, 1.2)

    straight_km    = route_length_km(points, start=start)
    distance_km    = straight_km * road_factor
    fuel_used_l    = (distance_km / 100) * fuel_consumption
    fuel_cost_som  = fuel_used_l * fuel_price
    travel_time_min = (distance_km / AVG_SPEED_KMH) * 60
    road_penalty   = road_factor

    D_norm = distance_km / 50.0
    C_norm = fuel_cost_som / 200.0
    T_norm = travel_time_min / 60.0
    R_norm = (road_penalty - 1.0) / 0.5

    score = (
        weights["w1"] * D_norm +
        weights["w2"] * C_norm +
        weights["w3"] * T_norm +
        weights["w4"] * R_norm
    )

    return {
        "distance_km":     round(distance_km, 2),
        "fuel_used_l":     round(fuel_used_l, 2),
        "fuel_cost_som":   round(fuel_cost_som, 2),
        "travel_time_min": round(travel_time_min, 1),
        "road_quality":    road_quality,
        "road_penalty":    road_penalty,
        "score":           round(score, 4),
    }


# ── Сравнение трёх профилей ───────────────────────────────────────────────

def compare_route_profiles(
    points: List[Dict],
    start: Optional[Dict] = None,
    road_quality: str = "medium",
    fuel_price: float = DEFAULT_FUEL_PRICE_SOM,
    fuel_consumption: float = DEFAULT_FUEL_L_PER_100KM,
) -> Dict:
    """
    Для каждого профиля OR-Tools строит свой оптимальный маршрут
    с разными весами критериев. Три профиля — три разных маршрута!
    """

    # Наивный порядок — без оптимизации
    naive_points = list(points)
    naive_score  = score_route(
        naive_points,
        start=start,
        road_quality=road_quality,
        weights=WEIGHT_PROFILES["balanced"],
        fuel_price=fuel_price,
        fuel_consumption=fuel_consumption,
    )

    # Для каждого профиля OR-Tools строит СВОЙ маршрут
    # с весами специфичными для этого профиля
    profile_configs = {
        "cheapest": {
            "weight_distance": 0.1,
            "weight_time":     0.2,
        },
        "fastest": {
            "weight_distance": 0.2,
            "weight_time":     0.6,
        },
        "balanced": {
            "weight_distance": 0.25,
            "weight_time":     0.25,
        },
    }

    results      = {}
    best_routes  = {}

    for profile_name, config in profile_configs.items():
        # OR-Tools оптимизирует маршрут под этот профиль
        optimized = _solve_with_ortools(
            points,
            start=start,
            road_quality=road_quality,
            weight_distance=config["weight_distance"],
            weight_time=config["weight_time"],
            fuel_price=fuel_price,
            fuel_consumption=fuel_consumption,
        )
        best_routes[profile_name] = optimized

        results[profile_name] = score_route(
            optimized,
            start=start,
            road_quality=road_quality,
            weights=WEIGHT_PROFILES[profile_name],
            fuel_price=fuel_price,
            fuel_consumption=fuel_consumption,
        )

    # Победители по каждому критерию
    cheapest_profile = min(results, key=lambda k: results[k]["fuel_cost_som"])
    fastest_profile  = min(results, key=lambda k: results[k]["travel_time_min"])
    best_score_key   = min(results, key=lambda k: results[k]["score"])

    # Экономия: наивный vs лучший оптимизированный
    best_cost = results[cheapest_profile]["fuel_cost_som"]
    best_time = results[fastest_profile]["travel_time_min"]
    best_dist = results[best_score_key]["distance_km"]

    naive_cost = naive_score["fuel_cost_som"]
    naive_time = naive_score["travel_time_min"]
    naive_dist = naive_score["distance_km"]

    money_saved = round(max(0.0, naive_cost - best_cost), 2)
    time_saved  = round(max(0.0, naive_time - best_time), 1)
    dist_saved  = round(max(0.0, naive_dist - best_dist), 2)
    money_pct   = round(
        money_saved / naive_cost * 100, 1
    ) if naive_cost > 0 else 0.0

    return {
        "profiles": results,
        "profile_routes": {
            name: route
            for name, route in best_routes.items()
        },
        "naive": {
            "distance_km":     naive_dist,
            "fuel_cost_som":   naive_cost,
            "travel_time_min": naive_time,
        },
        "winner": {
            "cheapest":   cheapest_profile,
            "fastest":    fastest_profile,
            "best_score": best_score_key,
        },
        "savings": {
            "money_som":   money_saved,
            "time_min":    time_saved,
            "distance_km": dist_saved,
            "money_pct":   money_pct,
        },
        "fuel_info": {
            "price_per_liter":       fuel_price,
            "consumption_per_100km": fuel_consumption,
        },
    }