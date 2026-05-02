from django.core.mail import EmailMultiAlternatives, send_mail
from django.conf import settings


def send_verification_email(user):
    verify_url = f"https://farm-production-8c2c.up.railway.app/api/accounts/verify-link/?email={user.email}&code={user.activation_code}"
    
    html_message = f"""
    <html><body style="font-family:Arial,sans-serif;background:#f8f9fa;padding:40px 20px">
      <div style="max-width:480px;margin:0 auto;background:white;border-radius:16px;overflow:hidden">
        <div style="background:#1C4A2A;padding:32px;text-align:center">
          <div style="font-size:48px">🌿</div>
          <h1 style="color:white;margin:12px 0 4px;font-size:22px">AgroPath KG</h1>
          <p style="color:#81C784;margin:0;font-size:13px">Свежее — прямо от фермера</p>
        </div>
        <div style="padding:32px">
          <h2 style="color:#1a1a1a;font-size:18px;margin:0 0 12px">Подтвердите ваш аккаунт</h2>
          <p style="color:#666;font-size:14px;line-height:1.6;margin:0 0 28px">
            Вы зарегистрировались в AgroPath KG.<br>
            Нажмите кнопку ниже чтобы подтвердить что это вы:
          </p>
          <div style="text-align:center;margin:0 0 28px">
            <a href="{verify_url}" style="display:inline-block;background:#1C4A2A;color:white;text-decoration:none;padding:16px 40px;border-radius:12px;font-size:16px;font-weight:bold">
              ✅ Да, это я — активировать аккаунт
            </a>
          </div>
          <p style="color:#999;font-size:12px;text-align:center;margin:0">
            Если вы не регистрировались — просто проигнорируйте это письмо
          </p>
        </div>
        <div style="background:#f8f9fa;padding:16px;text-align:center;border-top:1px solid #eee">
          <p style="color:#aaa;font-size:11px;margin:0">AgroPath KG · Бишкек, Кыргызстан</p>
        </div>
      </div>
    </body></html>
    """
    
    msg = EmailMultiAlternatives(
        subject="AgroPath KG — Подтверждение аккаунта",
        body=f"Для активации аккаунта перейдите по ссылке: {verify_url}",
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[user.email],
    )
    msg.attach_alternative(html_message, "text/html")
    msg.send()


def send_welcome_email(user):
    send_mail(
        subject="AgroPath KG — Аккаунт активирован!",
        message=f"Поздравляем, {user.email}! Ваш аккаунт успешно активирован.",
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=True,
    )