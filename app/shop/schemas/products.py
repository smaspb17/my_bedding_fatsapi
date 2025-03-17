from datetime import datetime, timedelta, timezone
from typing import Optional

from pydantic import BaseModel, field_serializer, Field

from app.shop.schemas.images import ImageView
from app.shop.schemas.tags import TagView

MOSCOW_TZ = timezone(timedelta(hours=3))  # UTC+3


class ProductBase(BaseModel):
    category_id: int | None = None
    title: str = Field(max_length=100)
    description: str
    care: str
    is_available: bool = Field(default=True)


class ProductCompactView(ProductBase):
    id: int
    created: datetime = Field(json_schema_extra={"example": "01.01.2025 12:00:00"})
    updated: datetime = Field(json_schema_extra={'example': "01.01.2025 12:00:00"})

    class Config:
        from_attributes = True

    @field_serializer("created", "updated")
    def serialize_datetime(self, dt: datetime, _info) -> str:
        """Меняем формат вывода даты-времени в response"""
        if dt.tzinfo is None:  # Если время без часового пояса, считаем, что оно в UTC
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(MOSCOW_TZ).strftime("%d.%m.%Y %H:%M:%S")


class ProductView(ProductCompactView):
    tags: list["TagView"]
    images: list["ImageView"]


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    category_id: int | None = None
    title: str | None = Field(None, max_length=100)
    description: str | None = None
    care: str | None = None
    is_available: bool | None = None


class ProductDelete(BaseModel):
    product_id: int = Field(json_schema_extra={"example": 1})
    message: str = Field(json_schema_extra={"example": "Product deleted successfully"})


class TagResponse(BaseModel):
    message: str
    product_id: int
    tag_id: int
    current_tags: list[TagView]
