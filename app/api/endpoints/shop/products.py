from datetime import timezone, datetime

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse
from sqlmodel import Session, select, exists, and_

from app.api.schemas.shop.error_schemas import (
    NotFoundErrorSchema,
    BadRequestErrorSchema,
)
from app.api.schemas.shop.products import (
    ProductView,
    ProductCreate,
    ProductUpdate,
    ProductDelete,
)
from app.db.database import SessionDep
from app.db.shop.models import ProductDB, CategoryDB

router = APIRouter(
    prefix="/product",
    tags=["Магазин: Товары"],
    responses={
        400: {"model": BadRequestErrorSchema, "description": "Bad request"},
        404: {"model": NotFoundErrorSchema, "description": "Not Found"},
    },
)


@router.get(
    "/list",
    summary="Получение всех товаров",
    description="Получение списка всех товаров",
    response_model=list[ProductView],
)
def product_list(session: SessionDep) -> list[ProductView]:
    products = session.exec(select(ProductDB)).all()
    return products


@router.get(
    "/list/{cat_id}",
    summary="Список товаров по категориям",
    description="Получение списка товаров по выбранной категориям",
    response_model=list[ProductView],
)
def product_list_by_cat(session: SessionDep, cat_id: int) -> list[ProductView]:
    category = session.get(CategoryDB, cat_id)
    if not category:
        raise HTTPException(
            status_code=404, detail=f"category with id={cat_id} not found"
        )
    # products = session.exec(
    #     select(ProductDB).where(ProductDB.category_id == cat_id)
    # ).all()
    products = category.products
    return products


@router.get(
    "/detail/{product_id}",
    summary="Получение товара",
    description="Получение товара",
    response_model=ProductView,
)
def product_detail(product_id: int, session: SessionDep) -> ProductView:
    product = session.get(ProductDB, product_id)
    if not product:
        raise HTTPException(
            status_code=404, detail=f"product with id={product_id} not found"
        )
    return product.model_dump()


@router.post(
    "/create",
    summary="Создание товара",
    description="Создание товара",
    response_model=ProductView,
    status_code=201,
    responses={
        201: {"model": ProductView, "description": "Product successfully created"},
    },
)
def product_create(product: ProductCreate, session: SessionDep) -> ProductView:
    cat_id = product.category_id
    category = session.get(CategoryDB, cat_id)
    if not category:
        raise HTTPException(
            status_code=404, detail=f"Category with id={cat_id} not found"
        )
    existing_product = session.exec(
        select(ProductDB).where(ProductDB.title == product.title)
    ).first()
    if existing_product:
        raise HTTPException(
            status_code=400, detail="Product with that title already exists."
        )
    product_db = ProductDB(**product.model_dump())
    session.add(product_db)
    session.commit()
    session.refresh(product_db)
    return ProductView(**product_db.model_dump())


@router.patch(
    "/update/{product_id}",
    summary="Частичное изменение товара",
    description="Частичное изменение товара",
    response_model=ProductView,
)
def product_update(
    product_id: int, product: ProductUpdate, session: SessionDep
) -> ProductView:
    product_db = session.get(ProductDB, product_id)
    if not product:
        raise HTTPException(
            status_code=404, detail=f"Product with id={product_id} not found"
        )
    stmt = select(
        exists().where(
            and_(ProductDB.title == product.title, ProductDB.id != product_id)
        )
    )
    is_exists = session.exec(stmt).first()
    if is_exists:
        raise HTTPException(
            status_code=400,
            detail="Product is already exists. Unique constraint failed: title field",
        )
    data = product.model_dump(exclude_unset=True).items()
    for field, value in data:
        setattr(product_db, field, value)
    product_db.updated = datetime.now(timezone.utc)
    session.commit()
    session.refresh(product_db)
    return product_db


@router.delete(
    "/delete/{product_id}",
    summary="Удаление товара",
    description="Удаление товара",
    response_model=ProductDelete,
)
def product_delete(
    product_id: int,
    session: SessionDep,
):
    product = session.get(ProductDB, product_id)
    if not product:
        raise HTTPException(
            status_code=404, detail=f"Product with id={product_id} not found"
        )
    session.delete(product)
    session.commit()
    return ProductDelete(product_id=product.id, message="Product deleted successfully")
