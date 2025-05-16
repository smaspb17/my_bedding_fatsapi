# email/service.py
import aiosmtplib
from email.message import EmailMessage

from app.core.config import settings  # или напрямую переменные


async def send_email(to_email: str, subject: str, html_body: str):
    message = EmailMessage()
    message["From"] = settings.SMTP_USER
    message["To"] = to_email
    message["Subject"] = subject
    message.set_content("Ваш почтовый клиент не поддерживает HTML")
    message.add_alternative(html_body, subtype="html")

    await aiosmtplib.send(
        message,
        hostname=settings.SMTP_HOST,
        port=settings.SMTP_PORT,
        username=settings.SMTP_USER,
        password=settings.SMTP_PASSWORD,
        use_tls=settings.SMTP_USE_TLS,
    )
