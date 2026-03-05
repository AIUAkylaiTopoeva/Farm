from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import FarmerProfile

User = get_user_model()


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)

    # Ограничиваем роли на регистрацию: только customer/farmer
    role = serializers.ChoiceField(
        choices=[User.Role.CUSTOMER, User.Role.FARMER],
        required=False,
        default=User.Role.CUSTOMER,
    )

    class Meta:
        model = User
        fields = ("email", "password", "role")

    def create(self, validated_data):
        role = validated_data.get("role", User.Role.CUSTOMER)

        user = User.objects.create_user(
            email=validated_data["email"],
            password=validated_data["password"],
            role=role,
        )

        if user.role == User.Role.FARMER:
            FarmerProfile.objects.create(user=user)

        return user

class FarmerProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = FarmerProfile
        fields = ("farm_name", "address", "lat", "lon")

class MeSerializer(serializers.ModelSerializer):
    farmer_profile = FarmerProfileSerializer(read_only=True)
    class Meta:
        model = User
        fields = ("id", "email", "role", "farmer_profile")
        