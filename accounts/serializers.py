from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import FarmerProfile
from .utils import send_verification_email
import threading

User = get_user_model()

def _send_async(user):
    def run():
        try:
            send_verification_email(user)
        except Exception as e:
            print(f"Email send error: {e}")
    threading.Thread(target=run, daemon=True).start()


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)
    role = serializers.ChoiceField(
        choices=[User.Role.CUSTOMER, User.Role.FARMER],
        required=False,
        default=User.Role.CUSTOMER,
    )

    class Meta:
        model = User
        fields = ("email", "password", "role")

    def validate_email(self, value):
        if User.objects.filter(email=value.lower()).exists():
            raise serializers.ValidationError(
                "Пользователь с таким email уже существует"
            )
        return value.lower()

    def create(self, validated_data):
        role = validated_data.get("role", User.Role.CUSTOMER)

        user = User.objects.create_user(
            email=validated_data["email"],
            password=validated_data["password"],
            role=role,
            is_active=False,
        )

        if user.role == User.Role.FARMER:
            FarmerProfile.objects.create(user=user)

        # Отправляем письмо асинхронно — не блокирует ответ
        _send_async(user)

        return user

class VerifyEmailSerializer(serializers.Serializer):
    email = serializers.EmailField()
    code = serializers.CharField(max_length=6, min_length=6)

    def validate_code(self, value):
        if not value.isdigit():
            raise serializers.ValidationError(
                "Код должен состоять из цифр"
            )
        return value


class FarmerProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = FarmerProfile
        fields = (
            "farm_name", "address",
            "lat", "lon",
            "cost_per_km", "vehicle_cap_kg",
            "is_verified"
        )
        read_only_fields = ("is_verified",)


class MeSerializer(serializers.ModelSerializer):
    farmer_profile = FarmerProfileSerializer(read_only=True)

    class Meta:
        model = User
        fields = (
            "id", "email", "role",
            "is_verified", "farmer_profile"
        )