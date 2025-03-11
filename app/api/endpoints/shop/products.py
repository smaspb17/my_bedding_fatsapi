from datetime import timezone, datetime

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import selectinload, joinedload
from sqlmodel import (
    Session,
    select,
    exists,
    and_,
)

from app.api.schemas.shop.error_schemas import (
    NotFoundErrorSchema,
    BadRequestErrorSchema,
)
from app.api.schemas.shop.products import (
    ProductView,
    ProductCreate,
    ProductUpdate,
    ProductDelete,
    TagResponse,
)
from app.db.database import SessionDep
from app.db.shop.models import ProductDB, CategoryDB, TagDB, ProductTagJoin

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
def product_list(
    session: SessionDep,
    page: int = 1,
    per_page: int = 5,
) -> list[ProductView]:
    # пагинация + жадная загрузка
    stmt = (
        select(ProductDB)
        .options(selectinload(ProductDB.tags))
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    products = session.exec(stmt).unique().all()
    return products


@router.get(
    "/list/{cat_id}",
    summary="Список товаров по категориям",
    description="Получение списка товаров по выбранной категориям",
    response_model=list[ProductView],
)
def product_list_by_cat(
    session: SessionDep,
    cat_id: int,
    page: int = 1,
    per_page: int = 5,
) -> list[ProductView]:
    category = session.get(CategoryDB, cat_id)
    if not category:
        raise HTTPException(
            status_code=404, detail=f"Category with id={cat_id} not found"
        )
    # пагинация + жадная загрузка
    stmt = (
        select(ProductDB)
        .options(selectinload(ProductDB.tags))
        .where(ProductDB.category_id == cat_id)
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    # # ленивая загрузка через relationship -> проблема N+1
    # category = session.get(CategoryDB, cat_id)
    # products = category.products
    products = session.exec(stmt).unique().all()
    # print(f'products {products}')

    return products


@router.get(
    "/detail/{product_id}",
    summary="Получение товара",
    description="Получение товара",
    response_model=ProductView,
)
def product_detail(product_id: int, session: SessionDep) -> ProductView:
    stmt = (
        select(ProductDB)
        .options(selectinload(ProductDB.tags))
        .where(ProductDB.id == product_id)
    )
    product = session.exec(stmt).first()
    # product = session.get(ProductDB, product_id)  # N+1 - ленивая загрузка
    if not product:
        raise HTTPException(
            status_code=404, detail=f"product with id={product_id} not found"
        )
    print(f'Product_tags: {product.tags}')
    return product


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
    stmt = select(exists().where(CategoryDB.id == cat_id))
    is_exists_category = session.exec(stmt).first()
    if not is_exists_category:
        raise HTTPException(
            status_code=404, detail=f"Category with id={cat_id} not found"
        )
    stmt = select(exists().where(ProductDB.title == product.title))
    is_exists_product = session.exec(stmt).first()
    # is_exists_product = session.exec(
    #     select(ProductDB).where(ProductDB.title == product.title)
    # ).first()
    if is_exists_product:
        raise HTTPException(
            status_code=400, detail="Product with that title already exists."
        )
    product_db = ProductDB(**product.model_dump())
    session.add(product_db)
    session.commit()
    session.refresh(product_db)
    return product_db


@router.patch(
    "/update/{product_id}",
    summary="Частичное изменение товара",
    description="Частичное изменение товара",
    response_model=ProductView,
)
def product_update(
        product_id: int,
        product: ProductUpdate,
        session: SessionDep
) -> ProductView:
    stmt = (
        select(ProductDB)
        .options(selectinload(ProductDB.tags))
        .where(ProductDB.id == product_id)
    )
    product_db = session.exec(stmt).first()
    # product_db = session.get(ProductDB, product_id)  # N+1 - ленивая загрузка
    if not product_db:
        raise HTTPException(
            status_code=404,
            detail=f"Product with id={product_id} not found. Please check the product ID and try "
            f"again.",
        )
    stmt = select(
        exists().where(
            and_(ProductDB.title == product.title, ProductDB.id != product_id)
        )
    )
    is_exists = session.exec(stmt).first()
    # is_exists = session.exec(
    #     select(ProductDB).where((ProductDB.title == product.title) & (ProductDB.id != product_id))
    # ).first()
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


@router.post(
    "/{product_id}/tags/{tag_id}",
    summary="Добавление тега к товару",
    description="Добавление тега к товару",
    response_model=TagResponse,
    status_code=200,
)
def add_tag(product_id: int, tag_id: int, session: SessionDep):
    stmt = (
        select(ProductDB)
        .options(selectinload(ProductDB.tags))
        .where(ProductDB.id == product_id)
    )
    product = session.exec(stmt).first()
    # product = session.get(ProductDB, product_id) # N+1 - ленивая загрузка
    tag = session.get(TagDB, tag_id)
    if not product:
        raise HTTPException(
            status_code=400, detail=f"Product with id={product_id} not found"
        )
    if not tag:
        raise HTTPException(status_code=400, detail=f"Tag with id={tag_id} not found")
    stmt = select(
        exists().where(
            and_(
                ProductTagJoin.product_id == product_id, ProductTagJoin.tag_id == tag_id
            )
        )
    )
    is_exists = session.exec(stmt).first()
    if is_exists:
        raise HTTPException(
            status_code=400, detail="Tag is already assigned to this product"
        )
    # product.tags.append(tag) #  N+1 если не lazy="joined"
    product_tag = ProductTagJoin(product_id=product_id, tag_id=tag_id)
    session.add(product_tag)
    session.commit()
    return {
        "message": "Tag added successfully",
        "product_id": product_id,
        "tag_id": tag_id,
        "current_tags": [tag.model_dump() for tag in product.tags],
    }


@router.delete(
    "/{product_id}/tags/{tag_id}",
    summary="Удаление тега у товара",
    description="Удаление тега у товара",
    response_model=TagResponse,
    status_code=200,
)
def delete_tag(product_id: int, tag_id: int, session: SessionDep):
    stmt = (
        select(ProductTagJoin)
        .where(and_(ProductTagJoin.product_id == product_id,
                    ProductTagJoin.tag_id == tag_id))
    )
    product_tag = session.exec(stmt).first()
    if not product_tag:
        raise HTTPException(
            status_code=404, detail="Tag is not assigned to this product"
        )
    # product.tags.remove(tag)  # N+1 если нет lazy="joined"
    session.delete(product_tag)
    session.commit()
    stmt = (
        select(ProductDB)
        .options(selectinload(ProductDB.tags))
        .where(ProductDB.id == product_id)
    )
    product_tags = session.exec(stmt).first().tags
    # product_tags = session.get(ProductDB, product_id).tags  # N+1 ленивая загрузка
    return {
        "message": "Tag deleted successfully",
        "product_id": product_id,
        "tag_id": tag_id,
        "current_tags": [tag.model_dump() for tag in product_tags],
    }
