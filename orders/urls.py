from django.urls import path
from .views import (
    OrderCreateView,
    OrderListView,
    OrderDetailView,
    OrderStatusUpdateView,
    ReviewListCreateView,
    ReviewDeleteView,
    LikeToggleView,
    ProductLikesView,
    AdminOrderListView,
    ReviewUpdateView,
    LikedProductsView,
)

urlpatterns = [
    path("orders/", OrderListView.as_view(), name="order-list"),
    path("orders/create/", OrderCreateView.as_view(), name="order-create"),
    path("orders/admin/", AdminOrderListView.as_view(), name="admin-orders"),
    path("orders/<int:pk>/", OrderDetailView.as_view(), name="order-detail"),
    path("orders/<int:pk>/status/", OrderStatusUpdateView.as_view(), name="order-status"),
    path("products/<int:product_id>/reviews/", ReviewListCreateView.as_view(), name="reviews"),
    path("reviews/<int:pk>/", ReviewDeleteView.as_view(), name="review-delete"),
    path("reviews/<int:pk>/edit/", ReviewUpdateView.as_view(), name="review-update"),  # ← новый
    path("products/<int:product_id>/like/", LikeToggleView.as_view(), name="like-toggle"),
    path("products/<int:product_id>/likes/", ProductLikesView.as_view(), name="likes-count"),
    path("products/liked/", LikedProductsView.as_view(), name="liked-products"),  # ← новый
]