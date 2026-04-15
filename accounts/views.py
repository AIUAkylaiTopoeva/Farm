from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.auth import get_user_model
from .serializers import (
    RegisterSerializer, MeSerializer,
    FarmerProfileSerializer, VerifyEmailSerializer
)
from .models import FarmerProfile
from .utils import send_verification_email, send_welcome_email

User = get_user_model()


class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(
            {
                "message": "Аккаунт создан. Проверьте email для подтверждения.",
                "email": user.email,
            },
            status=status.HTTP_201_CREATED,
        )


class VerifyEmailView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = VerifyEmailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"]
        code = serializer.validated_data["code"]

        try:
            user = User.objects.get(
                email=email,
                activation_code=code
            )
        except User.DoesNotExist:
            return Response(
                {"error": "Неверный код или email"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if user.is_verified:
            return Response(
                {"message": "Email уже подтверждён"}
            )

        user.is_active = True
        user.is_verified = True
        user.activation_code = ""
        user.save(update_fields=[
            "is_active", "is_verified", "activation_code"
        ])

        try:
            send_welcome_email(user)
        except Exception:
            pass

        return Response({
            "message": "Email успешно подтверждён! Теперь можете войти."
        })


class ResendCodeView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        email = request.data.get("email")
        if not email:
            return Response(
                {"error": "Email обязателен"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            user = User.objects.get(
                email=email,
                is_verified=False
            )
        except User.DoesNotExist:
            return Response(
                {"error": "Пользователь не найден или уже верифицирован"},
                status=status.HTTP_400_BAD_REQUEST
            )

        user.generate_activation_code()

        try:
            send_verification_email(user)
        except Exception as e:
            return Response(
                {"error": f"Ошибка отправки: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        return Response({
            "message": "Код повторно отправлен на email"
        })


class MeView(generics.GenericAPIView):
    serializer_class = MeSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        return Response(self.get_serializer(request.user).data)


class UpdateFarmerProfileView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request):
        try:
            profile = request.user.farmer_profile
        except FarmerProfile.DoesNotExist:
            return Response(
                {"error": "Профиль фермера не найден"},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = FarmerProfileSerializer(
            profile, data=request.data, partial=True
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )


class ChangeRoleView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request):
        new_role = request.data.get("role")
        allowed = ["farmer", "customer"]
        if new_role not in allowed:
            return Response(
                {"error": "Role must be farmer or customer"},
                status=status.HTTP_400_BAD_REQUEST
            )

        user = request.user
        user.role = new_role
        user.save(update_fields=["role"])

        if new_role == "farmer":
            FarmerProfile.objects.get_or_create(user=user)

        return Response({
            "role": user.role,
            "message": "Role updated successfully"
        })