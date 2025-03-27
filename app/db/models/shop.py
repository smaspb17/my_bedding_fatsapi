from pathlib import Path
from typing import Optional

from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, ForeignKey

from app.db.models.base import Base, int_pk, created_at, updated_at


class ProductTagJoin(Base):
    __tablename__ = "product_tag_join"
    product_id: Mapped[int] = mapped_column(ForeignKey("product.id"), primary_key=True)
    tag_id: Mapped[int] = mapped_column(ForeignKey("tag.id"), primary_key=True)


class Tag(Base):
    __tablename__ = "tag"
    id: Mapped[int_pk]
    name: Mapped[str] = mapped_column(String(50), unique=True)
    products: Mapped[list["Product"]] = relationship(
        secondary="product_tag_join",
        back_populates="tags",
    )


class Category(Base):
    __tablename__ = "category"
    id: Mapped[int_pk]
    title: Mapped[str] = mapped_column(String(100), unique=True)
    description: Mapped[str | None] = mapped_column(nullable=True)
    products: Mapped[list["Product"]] = relationship(
        back_populates="category",
    )


class Product(Base):
    __tablename__ = "product"
    id: Mapped[int_pk]
    category_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("category.id", ondelete="RESTRICT"),
    )
    title: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    description: Mapped[str]
    care: Mapped[str]
    is_available: Mapped[bool] = mapped_column(default=True)
    created: Mapped[created_at]
    updated: Mapped[updated_at]
    category: Mapped["Category"] = relationship(
        back_populates="products",
        lazy="joined"
    )
    tags: Mapped[list["Tag"]] = relationship(
        secondary="product_tag_join",
        back_populates="products",
    )
    images: Mapped[list['ProductImage']] = relationship(
        back_populates='product',
        cascade='all, delete-orphan'
    )


class ProductImage(Base):
    __tablename__ = 'product_image'
    id: Mapped[int_pk]
    product_id: Mapped[int] = mapped_column(ForeignKey('product.id', ondelete='CASCADE'))
    image_path: Mapped[str]
    product: Mapped['Product'] = relationship(back_populates='images')


# class ProductTagJoin(SQLModel, table=True):
#     __tablename__ = "product_tag_join"
#     product_id: int = Field(foreign_key="product.id", primary_key=True)
#     tag_id: int = Field(foreign_key="tag.id", primary_key=True)


# class CategoryBase(SQLModel):
#     title: str = Field(max_length=100, unique=True)
#     description: str


# class Category(CategoryBase, table=True):
#     __tablename__ = "category"
#     id: int = Field(
#         default=None, primary_key=True, sa_column_kwargs={"autoincrement": True}
#     )
#     products: list["Product"] = Relationship(
#         back_populates="category",
#         passive_deletes="all",
#         # sa_relationship_kwargs={"lazy": "joined"},  # не нужно так как не делам category.products
#     )


# class ProductBase(SQLModel):
#     category_id: int | None = Field(
#         default=None, foreign_key="category.id", ondelete="SET NULL"
#     )
#     title: str = Field(max_length=100, unique=True, index=True)
#     description: str
#     care: str
#     is_available: Optional[bool] = Field(default=True)


# class Product(ProductBase, table=True):
#     __tablename__ = "product"
#     id: int | None = Field(default=None, primary_key=True)
#     created: Optional[datetime] = Field(
#         default_factory=lambda: datetime.now(UTC),
#         # sa_column_kwargs={
#         #     # "type_": TIMESTAMP(timezone=True),
#         #     "server_default": text("now()")
#         # },
#         sa_column=Column(TIMESTAMP(timezone=True), server_default=text("now()")),
#     )
#     updated: Optional[datetime] = Field(
#         default_factory=lambda: datetime.now(UTC),
#         # sa_column_kwargs={
#         #     "type_": TIMESTAMP(timezone=True),
#         #     "server_default": text("now()"),
#         #     "onupdate": lambda: datetime.now(UTC)
#         # },
#         sa_column=Column(
#             TIMESTAMP(timezone=True),
#             server_default=text("now()"),
#             onupdate=lambda: datetime.now(UTC),
#         ),
#     )
#
#     category: Category = Relationship(
#         back_populates="products",
#         sa_relationship_kwargs={"lazy": "joined"},
#     )
#     tags: list["Tag"] = Relationship(
#         back_populates="products",
#         link_model=ProductTagJoin,
#         # cascade="all, delete-orphan",  # Добавлено каскадное удаление
#     )
#     # # lazy = "joined" или "subquery" - установка жадной загрузки во всех запросах
#     # # для session.get() или product.tags
#     # tags: list["Tag"] = Relationship(
#     #     back_populates="products", link_model=ProductTagJoin, lazy="joined"
#     # )
