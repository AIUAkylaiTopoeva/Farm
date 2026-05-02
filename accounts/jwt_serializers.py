from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer


class AgroTokenObtainPairSerializer(TokenObtainPairSerializer):
    default_error_messages = {
        "no_active_account": (
            "Аккаунт не активирован. Подтвердите email через ссылку из письма "
            "или запросите новый код на /api/accounts/resend-code/."
        ),
    }
