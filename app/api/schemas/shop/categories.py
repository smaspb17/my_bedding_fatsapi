from pydantic import BaseModel, ConfigDict, Field

from app.db.shop.models import CategoryBase


class CategoryCreate(CategoryBase):
    pass


class CategoryView(CategoryBase):
    id: int


class CategoryDelete(BaseModel):
    id: int = Field(example='1')
    message: str = Field(example='Object deleted successfully')


class CategoryUpdate(CategoryBase):
    title: str | None = None
    description: str | None = None
