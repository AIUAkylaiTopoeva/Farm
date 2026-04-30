from django.urls import path
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView
)
from .views import (
    RegisterView,
    MeView,
    UpdateFarmerProfileView,
    ChangeRoleView,
    VerifyEmailView,
    ResendCodeView,
    FarmersMapView,
    AdminUsersView,
    VerifyEmailLinkView,
)

urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path("login/", TokenObtainPairView.as_view(), name="jwt_login"),
    path("refresh/", TokenRefreshView.as_view(), name="jwt_refresh"),
    path("me/", MeView.as_view(), name="me"),
    path("verify/", VerifyEmailView.as_view(), name="verify-email"),
    path("resend-code/", ResendCodeView.as_view(), name="resend-code"),
    path("farmer/profile/", UpdateFarmerProfileView.as_view(), name="farmer-profile"),
    path("change-role/", ChangeRoleView.as_view(), name="change-role"),
    path("farmers/map/", FarmersMapView.as_view(), name="farmers-map"),
    path("users/", AdminUsersView.as_view(), name="admin-users"),
    path("verify-link/", VerifyEmailLinkView.as_view(), name="verify-email-link"),
]