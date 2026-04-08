from django.urls import path
from .views import OptimizeRouteView, CompareRouteView

urlpatterns = [
    path("optimize/", OptimizeRouteView.as_view(), name="optimize_route"),
    path("compare/", CompareRouteView.as_view(), name="compare_route"),
]