from fastapi import APIRouter, HTTPException
from sqlalchemy import exists
from sqlmodel import select, exists, and_
from fastapi.responses import JSONResponse

from app.api.schemas.shop.categories import (
    CategoryView,
    CategoryCreate,
    CategoryUpdate,
    CategoryDelete,
)
from app.api.schemas.shop.error_schemas import (
    NotFoundErrorSchema,
    BadRequestErrorSchema,
)
from app.db.database import SessionDep
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
def get_cat_list(session: SessionDep) -> list[CategoryView]:
    cats = session.exec(select(CategoryDB)).all()
    return cats


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
def create_cat(category: CategoryCreate, session: SessionDep) -> CategoryView:
    category_exists = session.exec(
        select(CategoryDB).where(CategoryDB.title == category.title)
    ).first()
    if category_exists:
        raise HTTPException(
            status_code=400,
            detail="Category is already exists. Unique constraint failed: title field",
        )
    category_db = CategoryDB(**category.model_dump())  # Создаем объект БД
    session.add(category_db)
    session.commit()
    session.refresh(category_db)
    return category_db


@router.patch(
    "/{cat_id}",
    summary="Частичное обновление категории",
    description="Частичное обновление категории товаров",
    response_model=CategoryView,
)
def update_cat(
    cat_id: int, category: CategoryUpdate, session: SessionDep
) -> CategoryView:
    category_db = session.get(CategoryDB, cat_id)
    if not category_db:
        raise HTTPException(
            status_code=404, detail=f"category with id={cat_id} not found"
        )
    stmt = select(
        exists().where(
            and_(CategoryDB.title == category.title, CategoryDB.id != cat_id)
        )
    )
    is_exists = session.exec(stmt).first()
    if is_exists:
        raise HTTPException(
            status_code=400,
            detail="Category is already exists. Unique constraint failed: title field",
        )
    data = category.model_dump(exclude_unset=True).items()
    for field, value in data:
        setattr(category_db, field, value)
    session.commit()
    session.refresh(category_db)
    return category_db


@router.delete(
    "/{cat_id}",
    summary="Удаление категории",
    description="Удаление категории товара",
    response_model=CategoryDelete,
)
def delete_cat(cat_id: int, session: SessionDep) -> CategoryDelete:
    category = session.exec(select(CategoryDB).where(CategoryDB.id == cat_id)).first()
    if not category:
        raise HTTPException(
            status_code=404, detail=f"category with id={cat_id} not found"
        )
    session.delete(category)
    session.commit()
    return CategoryDelete(
        id=category.id,
        message="Object deleted successfully",
    )
