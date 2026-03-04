from rest_framework.permissions import BasePermission


class IsFarmer(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role == "farmer")


class IsCustomer(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role == "customer")


class IsAdminRole(BasePermission):
    """
    Business-role admin (role='admin').
    In practice for Django admin-panel you also need is_staff/is_superuser.
    """
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role == "admin")