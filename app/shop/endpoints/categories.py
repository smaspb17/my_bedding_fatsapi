from fastapi import APIRouter, HTTPException
from sqlmodel import select, exists, and_

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
from app.db.shop.models import CategoryDB

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
async def get_category_list(session: AsyncSessionDep) -> list[CategoryView]:
    result = await session.execute(select(CategoryDB))
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
    category: CategoryCreate, session: AsyncSessionDep
) -> CategoryView:
    is_exists_category = await session.scalar(select(exists().where(CategoryDB.title == category.title)))

    # stmt = select(exists().where(CategoryDB.title == category.title))
    # result = await session.execute(stmt)
    # is_exists_category = result.scalars().first()

    # is_exists_category = session.execute(
    #     select(CategoryDB).where(CategoryDB.title == category.title)
    # ).first()

    if is_exists_category:
        raise HTTPException(
            status_code=400,
            detail="Category is already exists. Unique constraint failed: title field",
        )
    # category_db = CategoryDB(**category.model_dump())  # Создаем объект БД
    category_db = CategoryDB.model_validate(category)  # Создаем объект БД
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
    cat_id: int,
    category: CategoryUpdate,
    session: AsyncSessionDep,
) -> CategoryView:
    category_db = await session.get(CategoryDB, cat_id)
    if not category_db:
        raise HTTPException(
            status_code=404, detail=f"Category with id={cat_id} not found"
        )
    # stmt = select(
    #     exists().where(
    #         and_(CategoryDB.title == category.title, CategoryDB.id != cat_id)
    #     )
    # )
    # result = await session.execute(stmt)
    # is_exists = result.scalars().first()
    is_exists = await session.scalar(
        select(
            exists().where(CategoryDB.title == category.title, CategoryDB.id != cat_id)
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
async def category_delete(cat_id: int, session: AsyncSessionDep) -> CategoryDelete:
    result = await session.execute(select(CategoryDB).where(CategoryDB.id == cat_id))
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
