from typing import Annotated

import asyncio
from fastapi import APIRouter, HTTPException, Security
from fastapi_cache.decorator import cache
from sqlmodel import select, exists

from app.auth.schemas import TokenData
from app.auth.security import has_permissions
from app.shop.schemas.categories import (
    CategoryView,
    CategoryCreate,
    CategoryUpdate,
    CategoryDelete,
)
from app.shop.schemas.error_schemas import (
    NotFoundErrorSchema,
    BadRequestErrorSchema,
)
from app.db.database import AsyncSessionDep
from app.db.models.shop import Category

router = APIRouter(
    prefix="/catalog",
    tags=["Магазин: Категории"],
    responses={
        400: {"model": BadRequestErrorSchema, "description": "Bad request"},
        404: {"model": NotFoundErrorSchema, "description": "Not Found"},
    },
)


@router.get(
    "/",
    summary="Список категорий",
    description="Получение списка категорий товаров",
    response_model=list[CategoryView],
)
@cache(expire=60)
async def get_category_list(
    _: Annotated[TokenData, Security(has_permissions, scopes=['shop:read'])],
    session: AsyncSessionDep
) -> list[CategoryView]:
    result = await session.execute(select(Category).order_by(Category.id))
    await asyncio.sleep(3)
    return result.scalars().all()


@router.post(
    "/",
    summary="Создание категории",
    description="Создание категории товаров",
    response_model=CategoryView,
    responses={
        201: {"description": "Category successfully created", "model": CategoryView},
    },
    status_code=201,
)
async def category_create(
    _: Annotated[TokenData, Security(has_permissions, scopes=['shop:create'])],
    session: AsyncSessionDep,
    category: CategoryCreate,
) -> CategoryView:
    is_exists_category = await session.scalar(select(exists().where(Category.title == category.title)))

    # stmt = select(exists().where(Category.title == category.title))
    # result = await session.execute(stmt)
    # is_exists_category = result.scalars().first()

    # is_exists_category = session.execute(
    #     select(Category).where(Category.title == category.title)
    # ).first()

    if is_exists_category:
        raise HTTPException(
            status_code=400,
            detail="Category is already exists. Unique constraint failed: title field",
        )
    category_db = Category(**category.model_dump())  # Создаем объект БД
    # category_db = Category.model_validate(category)  # Есть только в SQLModel
    session.add(category_db)
    await session.commit()
    # session.refresh(category_db)  # expire_on_commit=False
    return category_db


@router.patch(
    "/{cat_id}",
    summary="Частичное обновление категории",
    description="Частичное обновление категории товаров",
    response_model=CategoryView,
)
async def category_update(
    _: Annotated[TokenData, Security(has_permissions, scopes=['shop:update'])],
    session: AsyncSessionDep,
    cat_id: int,
    category: CategoryUpdate,

) -> CategoryView:
    category_db = await session.get(Category, cat_id)
    if not category_db:
        raise HTTPException(
            status_code=404, detail=f"Category with id={cat_id} not found"
        )
    # stmt = select(
    #     exists().where(
    #         and_(Category.title == category.title, Category.id != cat_id)
    #     )
    # )
    # result = await session.execute(stmt)
    # is_exists = result.scalars().first()
    is_exists = await session.scalar(
        select(
            exists().where(Category.title == category.title, Category.id != cat_id)
        )
    )
    if is_exists:
        raise HTTPException(
            status_code=400,
            detail="Category is already exists. Unique constraint failed: title field",
        )
    # category_data = category.model_dump(exclude_unset=True)
    # category_db.sqlmodel_update(category_data)

    data = category.model_dump(exclude_unset=True).items()
    for field, value in data:
        setattr(category_db, field, value)

    await session.commit()
    # await session.refresh(category_db) # expire_on_commit=False
    return category_db


@router.delete(
    "/{cat_id}",
    summary="Удаление категории",
    description="Удаление категории товара",
    response_model=CategoryDelete,
)
async def category_delete(
    _: Annotated[TokenData, Security(has_permissions, scopes=['shop:delete'])],
    session: AsyncSessionDep,
    cat_id: int,
) -> CategoryDelete:
    result = await session.execute(select(Category).where(Category.id == cat_id))
    category = result.scalar()
    if not category:
        raise HTTPException(
            status_code=404, detail=f"category with id={cat_id} not found"
        )
    # category.products.clear()
    await session.delete(category)
    await session.commit()
    return CategoryDelete(
        id=category.id,
        message="Object deleted successfully",
    )
