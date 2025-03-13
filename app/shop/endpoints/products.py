from datetime import timezone, datetime

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy.orm import selectinload
from sqlmodel import (
    select,
    exists,
    and_,
)

from app.shop.schemas.error_schemas import (
    NotFoundErrorSchema,
    BadRequestErrorSchema,
)
from app.shop.schemas.products import (
    ProductView,
    ProductCreate,
    ProductUpdate,
    ProductDelete,
    TagResponse,
)
from app.db.database import AsyncSessionDep
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
async def product_list(
    session: AsyncSessionDep,
    page: int = 1,
    per_page: int = Query(default=5, le=10),
) -> list[ProductView]:
    # пагинация + жадная загрузка
    stmt = (
        select(ProductDB)
        .options(selectinload(ProductDB.tags))
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    result = await session.execute(stmt)
    products = result.scalars().all()
    print(f'products {products}')
    for product in products:
        print(f"Product: {product.title}, Tags: {[tag.name for tag in product.tags]}")
    return products


@router.get(
    "/list/{cat_id}",
    summary="Список товаров по категориям",
    description="Получение списка товаров по выбранной категориям",
    response_model=list[ProductView],
)
async def product_list_by_cat(
    session: AsyncSessionDep,
    cat_id: int,
    page: int = 1,
    per_page: int = 5,
) -> list[ProductView]:
    category = await session.get(CategoryDB, cat_id)
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
    result = await session.execute(stmt)
    products = result.scalars().all()
    return products


@router.get(
    "/detail/{product_id}",
    summary="Получение товара",
    description="Получение товара",
    response_model=ProductView,
)
async def product_detail(product_id: int, session: AsyncSessionDep) -> ProductView:
    stmt = (
        select(ProductDB)
        .options(selectinload(ProductDB.tags))
        .where(ProductDB.id == product_id)
    )
    result = await session.execute(stmt)
    product = result.scalar()
    # product = session.get(ProductDB, product_id)  # N+1 - ленивая загрузка
    if not product:
        raise HTTPException(
            status_code=404, detail=f"product with id={product_id} not found"
        )
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
async def product_create(
    product: ProductCreate, session: AsyncSessionDep
) -> ProductView:
    cat_id = product.category_id

    # stmt = select(exists().where(CategoryDB.id == cat_id))
    # result = await session.execute(stmt)
    # is_exists_category = result.scalar()
    is_exists_category = await session.scalar(
        select(exists().where(CategoryDB.id == cat_id))
    )
    if not is_exists_category:
        raise HTTPException(
            status_code=404, detail=f"Category with id={cat_id} not found"
        )

    # is_exists_product = session.execute(
    #     select(ProductDB).where(ProductDB.title == product.title)
    # ).first()

    # stmt = select(exists().where(ProductDB.title == product.title))
    # result = await session.execute(stmt)
    # is_exists_product = result.scalar()

    is_exists_product = await session.scalar(
        select(exists().where(ProductDB.title == product.title))
    )
    if is_exists_product:
        raise HTTPException(
            status_code=400, detail="Product with that title already exists."
        )
    # product_db = ProductDB(**product.model_dump())
    # product_db = ProductDB(**product.dict())
    product_db = ProductDB.model_validate(product)
    session.add(product_db)
    product_db.tags = []
    await session.commit()
    # await session.refresh(product_db, ["tags"])  # expire_on_commit=False
    return product_db


@router.patch(
    "/update/{product_id}",
    summary="Частичное изменение товара",
    description="Частичное изменение товара",
    response_model=ProductView,
)
async def product_update(
    product_id: int, product: ProductUpdate, session: AsyncSessionDep
) -> ProductView:
    stmt = (
        select(ProductDB)
        .options(selectinload(ProductDB.tags))
        .where(ProductDB.id == product_id)
    )
    result = await session.execute(stmt)
    product_db = result.scalar()
    # product_db = session.get(ProductDB, product_id)  # N+1 - ленивая загрузка
    if not product_db:
        raise HTTPException(
            status_code=404,
            detail=f"Product with id={product_id} not found. Please check the product ID and try "
            f"again.",
        )
    # stmt = select(
    #     exists().where(
    #         and_(ProductDB.title == product.title, ProductDB.id != product_id)
    #     )
    # )
    # is_exists = await session.execute(stmt).first()

    # is_exists = session.execute(
    #     select(ProductDB).where((ProductDB.title == product.title) & (ProductDB.id != product_id))
    # ).first()

    is_exists = await session.scalar(
        select(
            exists().where(ProductDB.title == product.title, ProductDB.id != product_id)
        )
    )

    if is_exists:
        raise HTTPException(
            status_code=400,
            detail="Product is already exists. Unique constraint failed: title field",
        )
    data = product.model_dump(exclude_unset=True).items()
    for field, value in data:
        setattr(product_db, field, value)

    # product_data = product.model_dump(exclude_unset=True)
    # product_db.sqlmodel_update(product_data)

    product_db.updated = datetime.now(timezone.utc)
    await session.commit()
    # await session.refresh(product_db)  # expire_on_commit=False
    return product_db


@router.delete(
    "/delete/{product_id}",
    summary="Удаление товара",
    description="Удаление товара",
    response_model=ProductDelete,
)
async def product_delete(
    product_id: int,
    session: AsyncSessionDep,
):
    product = await session.get(ProductDB, product_id)
    if not product:
        raise HTTPException(
            status_code=404, detail=f"Product with id={product_id} not found"
        )
    await session.delete(product)
    await session.commit()
    return ProductDelete(product_id=product.id, message="Product deleted successfully")


@router.post(
    "/{product_id}/tags/{tag_id}",
    summary="Добавление тега к товару",
    description="Добавление тега к товару",
    response_model=TagResponse,
    status_code=201,
)
async def add_tag(product_id: int, tag_id: int, session: AsyncSessionDep):
    product = await session.get(
        ProductDB, product_id, options=[selectinload(ProductDB.tags)]
    )
    tag = await session.get(TagDB, tag_id)
    if not product:
        raise HTTPException(
            status_code=400, detail=f"Product with id={product_id} not found"
        )
    if not tag:
        raise HTTPException(status_code=400, detail=f"Tag with id={tag_id} not found")
    is_exists = await session.scalar(
        select(
            exists().where(
                ProductTagJoin.product_id == product_id, ProductTagJoin.tag_id == tag_id
            )
        )
    )
    if is_exists:
        raise HTTPException(
            status_code=400, detail="Tag is already assigned to this product"
        )
    # product.tags.append(tag) #  N+1 если не lazy="joined"
    product_tag = ProductTagJoin(product_id=product_id, tag_id=tag_id)
    session.add(product_tag)
    await session.commit()
    product.tags.append(tag)
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
async def delete_tag(product_id: int, tag_id: int, session: AsyncSessionDep):
    stmt = select(ProductTagJoin).where(
        and_(ProductTagJoin.product_id == product_id, ProductTagJoin.tag_id == tag_id)
    )
    result = await session.execute(stmt)
    product_tag = result.scalar()
    if not product_tag:
        raise HTTPException(
            status_code=404, detail="Tag is not assigned to this product"
        )
    # product.tags.remove(tag)  # N+1 если нет lazy="joined"
    await session.delete(product_tag)
    await session.commit()
    # stmt = (
    #     select(ProductDB)
    #     .options(selectinload(ProductDB.tags))
    #     .where(ProductDB.id == product_id)
    # )
    # product_tags = session.execute(stmt).first().tags
    product = await session.get(
        ProductDB, product_id, options=[selectinload(ProductDB.tags)]
    )  # N+1 ленивая
    # загрузка
    return {
        "message": "Tag deleted successfully",
        "product_id": product_id,
        "tag_id": tag_id,
        "current_tags": [tag.model_dump() for tag in product.tags],
    }
