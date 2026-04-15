from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsFarmer(BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role == "farmer"
        )


class IsCustomer(BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role == "customer"
        )


class IsAdminRole(BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role == "admin"
        )


class IsOwnerOrAdminRole(BasePermission):
    """Владелец объекта или админ."""
    def has_object_permission(self, request, view, obj):
        return bool(
            request.user
            and request.user.is_authenticated
            and (
                obj.owner_id == request.user.id
                or request.user.role == "admin"
            )
        )


class IsVerifiedFarmer(BasePermission):
    """Только верифицированный фермер (is_verified=True в FarmerProfile)."""
    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        if request.user.role != "farmer":
            return False
        try:
            return request.user.farmer_profile.is_verified
        except Exception:
            return False


class IsEmailVerified(BasePermission):
    """Пользователь подтвердил email."""
    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.is_verified
        )


class ReadOnly(BasePermission):
    """Только чтение."""
    def has_permission(self, request, view):
        return request.method in SAFE_METHODS