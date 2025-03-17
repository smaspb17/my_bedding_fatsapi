import asyncio
import os
from pathlib import Path

import aiofiles

from fastapi import UploadFile, File, HTTPException, APIRouter
from sqlalchemy import select, exists
from sqlalchemy.orm import joinedload

from app.db.database import AsyncSessionDep
from app.db.models.shop import ProductImage, Product
from app.shop.schemas.error_schemas import BadRequestErrorSchema, NotFoundErrorSchema
from app.shop.schemas.images import ImageView

router = APIRouter(
    prefix="/images",
    tags=["Магазин: Фотографии товаров"],
    responses={
        400: {"model": BadRequestErrorSchema, "description": "Bad request"},
        404: {"model": NotFoundErrorSchema, "description": "Not Found"},
    },
)


UPLOAD_FOLDER = Path(__file__).parent.parent.parent.parent / "media/products"
UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)


@router.post(
    "/upload/{product_id}",
    summary="Добавить фотографии товара",
    description="Добавить фотографии товара",
)
async def upload_product_images(
    session: AsyncSessionDep,
    product_id: int,
    files: list[UploadFile],
):
    # Проверяем, существует ли товар с таким ID
    query = select(exists().where(Product.id == product_id))
    product = await session.execute(query)
    if not product.scalar():
        raise HTTPException(status_code=404, detail="Product not found")

    product_folder = Path(UPLOAD_FOLDER) / str(product_id)
    product_folder.mkdir(parents=True, exist_ok=True)

    async def save_file(file: UploadFile):
        filename = file.filename
        file_location = product_folder / filename
        try:
            async with aiofiles.open(file_location, "wb") as buffer:
                await buffer.write(await file.read())
            # Создаем запись об изображении в базе данных
            product_image = ProductImage(
                product_id=product_id, image_path=str(file_location)
            )
            session.add(product_image)
            return {filename: str(file_location)}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error saving {filename}: {e}")

    result = await asyncio.gather(*[save_file(file) for file in files])

    await session.commit()
    return result


@router.get(
    "/{product_id}",
    summary="Получить фотографии товара",
    description="Получить фотографии товара",
    response_model=list[ImageView],
)
async def download_product_images(
    session: AsyncSessionDep,
    product_id: int,
) -> list[ImageView]:
    query = (
        select(Product)
        .options(joinedload(Product.images))
        .where(Product.id == product_id)
    )
    result = await session.execute(query)
    product = result.scalar()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    return [ImageView.model_validate(image) for image in product.images]
