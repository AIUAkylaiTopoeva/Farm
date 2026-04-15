from django.core.mail import send_mail
from django.conf import settings


def send_verification_email(user):
    send_mail(
        subject="AgroPath KG — Подтверждение email",
        message=f"""
Добро пожаловать в AgroPath KG!

Ваш код подтверждения: {user.activation_code}

Введите этот код в приложении для активации аккаунта.
Код действителен 24 часа.

Если вы не регистрировались — просто проигнорируйте это письмо.
        """,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=False,
    )


def send_welcome_email(user):
    send_mail(
        subject="AgroPath KG — Аккаунт активирован!",
        message=f"""
Поздравляем, {user.email}!

Ваш аккаунт успешно активирован.
Роль: {"Фермер" if user.role == "farmer" else "Покупатель"}

Теперь вы можете войти в приложение AgroPath KG.
        """,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=True,
    )