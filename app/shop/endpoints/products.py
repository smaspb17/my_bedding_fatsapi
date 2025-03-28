import asyncio
from datetime import timezone, datetime, UTC

from fastapi import APIRouter, HTTPException, Query
from fastapi_cache.decorator import cache
from sqlalchemy.orm import selectinload, joinedload
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
    ProductCompactView,
)
from app.db.database import AsyncSessionDep
from app.db.models.shop import Product, Category, Tag, ProductTagJoin
from app.shop.schemas.tags import TagView

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
@cache(expire=30)
async def product_list(
    session: AsyncSessionDep,
    page: int = 1,
    per_page: int = Query(default=5, le=10),
) -> list[ProductView]:
    # пагинация + жадная загрузка
    stmt = (
        select(Product)
        .options(selectinload(Product.tags))
        .options(joinedload(Product.images))
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    result = await session.execute(stmt)
    products = result.scalars().unique().all()
    await asyncio.sleep(3)
    return [ProductView.model_validate(product) for product in products]


@router.get(
    "/list/{cat_id}",
    summary="Список товаров по категориям",
    description="Получение списка товаров по выбранной категориям",
    response_model=list[ProductView],
)
@cache(expire=60)
async def product_list_by_cat(
    session: AsyncSessionDep,
    cat_id: int,
    page: int = 1,
    per_page: int = 5,
) -> list[ProductView]:
    category = await session.get(Category, cat_id)
    if not category:
        raise HTTPException(
            status_code=404, detail=f"Category with id={cat_id} not found"
        )
    # пагинация + жадная загрузка
    stmt = (
        select(Product)
        .options(selectinload(Product.tags))
        .options(joinedload(Product.images))
        .where(Product.category_id == cat_id)
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    # # ленивая загрузка через relationship -> проблема N+1
    # category = session.get(Category, cat_id)
    # products = category.products
    result = await session.execute(stmt)
    products = result.scalars().unique().all()
    await asyncio.sleep(3)
    return [ProductView.model_validate(product) for product in products]


@router.get(
    "/detail/{product_id}",
    summary="Получение товара",
    description="Получение товара",
    response_model=ProductView,
)
@cache(expire=60)
async def product_detail(product_id: int, session: AsyncSessionDep) -> ProductView:
    stmt = (
        select(Product)
        .options(selectinload(Product.tags))
        .options(joinedload(Product.images))
        .where(Product.id == product_id)
    )
    result = await session.execute(stmt)
    product = result.scalar()
    # product = session.get(Product, product_id)  # N+1 - ленивая загрузка
    if not product:
        raise HTTPException(
            status_code=404, detail=f"product with id={product_id} not found"
        )
    await asyncio.sleep(3)
    return ProductView.model_validate(product)


@router.post(
    "/create",
    summary="Создание товара",
    description="Создание товара",
    response_model=ProductCompactView,
    status_code=201,
    responses={
        201: {"model": ProductCompactView, "description": "Product successfully created"},
    },
)
async def product_create(
    product: ProductCreate, session: AsyncSessionDep
) -> ProductCompactView:
    category_id = product.category_id
    is_exists_category = await session.scalar(
        select(exists().where(Category.id == category_id))
    )
    if not is_exists_category:
        raise HTTPException(
            status_code=404, detail=f"Category with id={category_id} not found"
        )
    is_exists_product = await session.scalar(
        select(exists().where(Product.title == product.title))
    )
    if is_exists_product:
        raise HTTPException(
            status_code=400, detail="Product with that title already exists."
        )
    # product_db = Product.model_validate(product)  # для валидации в Pydantic
    # product_db = Product(**product.dict())
    product_db = Product(**product.model_dump())
    session.add(product_db)
    await session.commit()
    # await session.refresh(product_db, ["tags"])  # expire_on_commit=False
    return ProductCompactView.model_validate(product_db)


@router.patch(
    "/update/{product_id}",
    summary="Частичное изменение товара",
    description="Частичное изменение товара",
    response_model=ProductCompactView,
)
async def product_update(
    product_id: int, product: ProductUpdate, session: AsyncSessionDep
) -> ProductCompactView:
    product_db = await session.get(Product, product_id)
    if not product_db:
        raise HTTPException(
            status_code=404,
            detail=f"Product with id={product_id} not found. Please check the product ID and try "
            f"again.",
        )
    is_exists = await session.scalar(
        select(exists().where(Product.title == product.title, Product.id != product_id))
    )
    if is_exists:
        raise HTTPException(
            status_code=400,
            detail="Product is already exists. Unique constraint failed: title field",
        )
    data = product.model_dump(exclude_unset=True).items()
    for field, value in data:
        if field == "is_available" and value is None:
            raise HTTPException(
                status_code=400,
                detail="Invalid request: is_available field should not be None.",
            )
        setattr(product_db, field, value)

    # product_data = product.model_dump(exclude_unset=True)
    # product_db.sqlmodel_update(product_data)

    product_db.updated = datetime.now(UTC)
    await session.commit()
    # await session.refresh(product_db)  # expire_on_commit=False
    return ProductCompactView.model_validate(product_db)


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
    product = await session.get(Product, product_id)
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
    print()
    print("ПОлучение product")
    product = await session.get(
        Product, product_id, options=[selectinload(Product.tags)]
    )
    print()
    print("Получение тега")
    tag = await session.get(Tag, tag_id)
    print()
    if not product:
        raise HTTPException(
            status_code=400, detail=f"Product with id={product_id} not found"
        )
    if not tag:
        raise HTTPException(status_code=400, detail=f"Tag with id={tag_id} not found")
    print("Есть ли уже такая же связь")
    is_exists = await session.scalar(
        select(
            exists().where(
                ProductTagJoin.product_id == product_id, ProductTagJoin.tag_id == tag_id
            )
        )
    )
    print()
    if is_exists:
        raise HTTPException(
            status_code=400, detail="Tag is already assigned to this product"
        )
    product.tags.append(tag)  # риск N+1 -> тут его нет по логам
    # product_tag = ProductTagJoin(product_id=product_id, tag_id=tag_id)
    # session.add(product_tag)
    await session.commit()
    return {
        "message": "Tag added successfully",
        "product_id": product_id,
        "tag_id": tag_id,
        "current_tags": [TagView.model_validate(tag) for tag in product.tags],
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
    print()
    print("проверка наличия связи")
    result = await session.execute(stmt)
    product_tag = result.scalar()
    if not product_tag:
        raise HTTPException(
            status_code=404, detail="Tag is not assigned to this product"
        )
    # product.tags.remove(tag)  # N+1 если нет lazy="joined"
    print()
    await session.delete(product_tag)
    print("Удаление связи")
    await session.commit()
    print()
    print("Жадная хитрая загрузка тегов")
    product = await session.get(
        Product, product_id, options=[selectinload(Product.tags)]
    )  # N+1 ленивая
    # загрузка
    print()
    print("Вывод результатов")
    return {
        "message": "Tag deleted successfully",
        "product_id": product_id,
        "tag_id": tag_id,
        "current_tags": [TagView.model_validate(tag) for tag in product.tags],
    }
