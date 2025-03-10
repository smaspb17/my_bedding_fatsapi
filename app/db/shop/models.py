from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Field, SQLModel, Relationship, Column, TIMESTAMP


class CategoryBase(SQLModel):
    title: str = Field(max_length=100, unique=True)
    description: str


class CategoryDB(CategoryBase, table=True):
    __tablename__ = "category"
    id: int | None = Field(default=None, primary_key=True)
    products: list["ProductDB"] = Relationship(back_populates="category")


class ProductBase(SQLModel):
    category_id: int | None = Field(default=None, foreign_key="category.id", ondelete='SET NULL')
    title: str = Field(max_length=100, unique=True)
    description: str
    care: str
    is_available: Optional[bool] = Field(default=True)


class ProductDB(ProductBase, table=True):
    __tablename__ = "product"
    id: int | None = Field(default=None, primary_key=True)
    created: Optional[datetime] = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(TIMESTAMP(timezone=True)),
    )
    updated: Optional[datetime] = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(TIMESTAMP(timezone=True)),
    )
    category: CategoryDB = Relationship(back_populates="products")
