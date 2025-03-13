from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Field, SQLModel, Relationship, Column, TIMESTAMP
from sqlalchemy import Column, Integer


class ProductTagJoin(SQLModel, table=True):
    __tablename__ = "product_tag_join"
    product_id: int = Field(foreign_key="product.id", primary_key=True)
    tag_id: int = Field(foreign_key="tag.id", primary_key=True)


# # Вариант M2M с SQLAlchemy - для простых связей.
# product_tag = Table(
#     "product_tag",
#     Base.metadata,
#     Column("product_id", ForeignKey("products.id"), primary_key=True),
#     Column("tag_id", ForeignKey("tags.id"), primary_key=True),
# )
# tags: list['TagDB'] = Relationship(
#     "TagDB", secondary="product_tag", back_populates="products", lazy="subquery"
# )


class CategoryBase(SQLModel):
    title: str = Field(max_length=100, unique=True)
    description: str


class CategoryDB(CategoryBase, table=True):
    __tablename__ = "category"
    id: int = Field(
        default=None,
        primary_key=True,
        sa_column_kwargs={"autoincrement": True}
    )
    products: list["ProductDB"] = Relationship(
        back_populates="category",
        passive_deletes="all",
        # sa_relationship_kwargs={"lazy": "joined"},  # не нужно так как не делам category.products
    )


class ProductBase(SQLModel):
    category_id: int | None = Field(
        default=None, foreign_key="category.id", ondelete="SET NULL"
    )
    title: str = Field(max_length=100, unique=True, index=True)
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

    category: CategoryDB = Relationship(
        back_populates="products",
        sa_relationship_kwargs={"lazy": "joined"},
    )
    tags: list["TagDB"] = Relationship(
        back_populates="products",
        link_model=ProductTagJoin,
        # cascade="all, delete-orphan",  # Добавлено каскадное удаление
    )
    # # lazy = "joined" или "subquery" - установка жадной загрузки во всех запросах
    # # для session.get() или product.tags
    # tags: list["TagDB"] = Relationship(
    #     back_populates="products", link_model=ProductTagJoin, lazy="joined"
    # )


class TagBase(SQLModel):
    name: str = Field(max_length=50, unique=True)


class TagDB(TagBase, table=True):
    __tablename__ = "tag"
    id: int | None = Field(default=None, primary_key=True)
    products: list[ProductDB] = Relationship(
        back_populates="tags",
        link_model=ProductTagJoin,
        # cascade="all, delete-orphan",  # Добавлено каскадное удаление
    )


# class ImageBase(SQLModel):
#     product_id: int = Field(foreign_key='product.id', ondelete='CASCADE')
#     image =
