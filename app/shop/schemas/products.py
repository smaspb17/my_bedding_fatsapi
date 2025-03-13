from datetime import datetime, timedelta, timezone

from pydantic import BaseModel, field_serializer, Field

from app.shop.schemas.tags import TagView
from app.db.shop.models import ProductBase

MOSCOW_TZ = timezone(timedelta(hours=3))  # UTC+3


class ProductView(ProductBase):
    id: int
    created: datetime = Field(json_schema_extra={"example": "01.01.2025 12:00:00"})
    updated: datetime = Field(json_schema_extra={'example': "01.01.2025 12:00:00"})
    tags: list[TagView]

    @field_serializer("created", "updated")
    def serialize_datetime(self, dt: datetime, _info) -> str:
        """Меняем формат вывода даты-времени в response"""
        if dt.tzinfo is None:  # Если время без часового пояса, считаем, что оно в UTC
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(MOSCOW_TZ).strftime("%d.%m.%Y %H:%M:%S")


class ProductCreate(ProductBase):
    # tags: list[TagView] = []
    pass


class ProductUpdate(BaseModel):
    category_id: int | None = None
    title: str | None = None
    description: str | None = None
    care: str | None = None
    is_available: bool | None = None


class ProductDelete(BaseModel):
    product_id: int = Field(json_schema_extra={"example": "1"})
    message: str = Field(json_schema_extra={"example": "Product deleted successfully"})


class TagResponse(BaseModel):
    message: str
    product_id: int
    tag_id: int
    current_tags: list[TagView]
