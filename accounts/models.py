from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.utils.crypto import get_random_string


class UserManager(BaseUserManager):
    def _create(self, email: str, password: str | None, **extra_fields):
        if not email:
            raise ValueError("Email is required")
        email = self.normalize_email(email).lower()
        user = self.model(email=email, **extra_fields)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        if not user.activation_code:
            user.activation_code = get_random_string(10)
        user.save(using=self._db)
        return user

    def create_user(self, email: str, password: str | None = None, **extra_fields):
        extra_fields.setdefault("is_active", True)
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        extra_fields.setdefault("role", User.Role.CUSTOMER)
        return self._create(email, password, **extra_fields)

    def create_superuser(self, email: str, password: str | None = None, **extra_fields):
        extra_fields.setdefault("role", User.Role.ADMIN)
        extra_fields.setdefault("is_active", True)
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self._create(email, password, **extra_fields)


class User(AbstractUser):
    class Role(models.TextChoices):
        FARMER = "farmer", "Farmer"
        CUSTOMER = "customer", "Customer"
        ADMIN = "admin", "Admin"

    username = None
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.CUSTOMER)
    activation_code = models.CharField(max_length=20, blank=True, default="")

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    def __str__(self):
        return self.email


class FarmerProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="farmer_profile")

    farm_name = models.CharField(max_length=200, blank=True, default="")
    address = models.CharField(max_length=255, blank=True, default="")
    lat = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    lon = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

    # Поля для расчёта стоимости доставки
    cost_per_km = models.FloatField(
        default=15.0,
        help_text="Стоимость доставки за 1 км (сом)"
    )
    vehicle_cap_kg = models.FloatField(
        default=500.0,
        help_text="Грузоподъёмность транспортного средства (кг)"
    )

    is_verified = models.BooleanField(
        default=False,
        help_text="Верифицирован администратором"
    ) 

    def __str__(self):
        return f"FarmerProfile({self.user.email})"