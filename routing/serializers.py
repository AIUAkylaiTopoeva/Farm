from rest_framework import serializers


class LatLonSerializer(serializers.Serializer):
    lat = serializers.FloatField()
    lon = serializers.FloatField()


class OptimizeRouteRequestSerializer(serializers.Serializer):
    product_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        allow_empty=False,
    )
    start = LatLonSerializer(required=False)

    def validate_product_ids(self, value):
        seen = set()
        unique = []
        for x in value:
            if x not in seen:
                unique.append(x)
                seen.add(x)
        return unique


class CompareRouteRequestSerializer(serializers.Serializer):
    """Для /api/routing/compare/ — добавляет road_quality."""
    product_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        allow_empty=False,
    )
    start = LatLonSerializer(required=False)
    road_quality = serializers.ChoiceField(
        choices=["good", "medium", "bad"],
        default="medium",
        required=False,
    )

    def validate_product_ids(self, value):
        seen = set()
        unique = []
        for x in value:
            if x not in seen:
                unique.append(x)
                seen.add(x)
        return unique


class RoutePointSerializer(serializers.Serializer):
    farmer_id = serializers.IntegerField()
    farm_name = serializers.CharField(allow_blank=True)
    address = serializers.CharField(allow_blank=True)
    lat = serializers.FloatField()
    lon = serializers.FloatField()
    product_ids = serializers.ListField(child=serializers.IntegerField())


class OptimizeRouteResponseSerializer(serializers.Serializer):
    naive_order_farmer_ids = serializers.ListField(child=serializers.IntegerField())
    optimized_order_farmer_ids = serializers.ListField(child=serializers.IntegerField())
    naive_distance_km = serializers.FloatField()
    optimized_distance_km = serializers.FloatField()
    points = RoutePointSerializer(many=True)