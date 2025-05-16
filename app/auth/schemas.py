from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, EmailStr, Field, field_serializer
from typing import Annotated, Optional

from pygments.lexer import default

from app.shop.schemas.products import MOSCOW_TZ


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    email: str | None = None
    scopes: list[str] = []


class RoleEnum(str, Enum):
    BUYER = "buyer"
    MANAGER = "manager"
    ADMIN = "admin"


class RegisterUserCreate(BaseModel):
    role: RoleEnum
    email: EmailStr
    phone_number: str
    is_active: bool | None = None
    first_name: str | None = None
    last_name: str | None = None
    password: str
    repeat_password: str
    model_config = {"extra": "forbid"}


class RegisterUserPublic(BaseModel):
    id: int
    email: str
    phone_number: str
    role: str
    first_name: str | None = None
    last_name: str | None = None
    address: str | None = None
    photo: str | None = None
    telegram_id: str | None = None
    telegram_username: str | None = None
    is_active: bool
    created: datetime = Field(
        json_schema_extra={"example": "01.01.2025 12:00:00"}
    )
    updated: datetime = Field(
        json_schema_extra={"example": "01.01.2025 12:00:00"}
    )

    class Config:
        from_attributes = True

    @field_serializer("created", "updated")
    def serialize_datetime(self, dt: datetime, _info) -> str:
        """Меняем формат вывода даты-времени в response"""
        if (
            dt.tzinfo is None
        ):  # Если время без часового пояса, считаем, что оно в UTC
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(MOSCOW_TZ).strftime("%d.%m.%Y %H:%M:%S")


class ChangePassword(BaseModel):
    old_password: str
    new_password: str
    repeat_password: str
    model_config = {
        "extra": "forbid"
    }  # Запрещает передачу дополнительных полей, не описанных в модели


class SetPassword(BaseModel):
    email: str
    token: str
    password: str
    repeat_password: str
    model_config = {"extra": "forbid"}
