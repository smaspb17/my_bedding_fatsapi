from app.core.config import settings
import hashlib
import uuid


def generate_confirm_token(email: str) -> str:
    """
    Генерация уникального токена на основе email пользователя
    """
    token = hashlib.sha256(f"{email}{uuid.uuid4()}".encode()).hexdigest()
    return token


def generate_email_confirmation_link(token: str) -> str:
    """
    Генерация ссылки для подтверждения email пользователя
    """
    confirmation_url = f"{settings.SITE_URL}/auth/confirm_email?token={token}"
    return confirmation_url


def generate_reset_password_link(email: str, token: str) -> str:
    """
    Генерация ссылки для сброса пароля пользователя
    """
    reset_password_url = (
        f"{settings.SITE_URL}/auth/reset_password_confirm"
        f"?email={email}&token={token}"
    )
    return reset_password_url
