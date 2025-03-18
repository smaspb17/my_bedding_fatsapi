import asyncio
import os
from pathlib import Path

import aiofiles

from fastapi import UploadFile, File, HTTPException, APIRouter
from sqlalchemy import select, exists, delete, and_
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


@router.get(
    "/{product_id}",
    summary="Получить все изображения товара",
    description="Получить все изображения товара",
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


@router.post(
    "/upload/{product_id}",
    summary="Добавить изображения к товару",
    description="Добавить изображения к товару",
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


@router.put(
    "/{product_id}/{image_id}",
    summary="Обновить изображение товара",
    description="Заменяет конкретное изображение товара новым файлом",
)
async def update_product_image(
    session: AsyncSessionDep,
    product_id: int,
    image_id: int,
    file: UploadFile = File(...),
):
    # проверка наличия товара
    exists_product = await session.scalar(
        select(exists().where(Product.id == product_id))
    )
    if not exists_product:
        raise HTTPException(status_code=404, detail="Product not found")
    # получение и проверка наличия файла с картинкой
    query = select(ProductImage).where(
        ProductImage.id == image_id, ProductImage.product_id == product_id
    )
    result = await session.execute(query)
    image = result.scalar()
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")

    # Удаляем старый файл
    old_image_path = Path(image.image_path)
    if old_image_path.exists():
        old_image_path.unlink()

    # Сохраняем новый файл
    product_folder = Path(UPLOAD_FOLDER) / str(product_id)
    product_folder.mkdir(parents=True, exist_ok=True)
    new_file_location = product_folder / file.filename
    async with aiofiles.open(new_file_location, "wb") as buffer:
        await buffer.write(await file.read())

    # Обновляем запись в БД
    image.image_path = str(new_file_location)
    await session.commit()

    return {
        "message": "Image updated successfully",
        "new_image_path": str(new_file_location),
    }


@router.delete(
    "/{product_id}/all",
    summary="Удалить все изображения товара",
    description="Удаляет все изображения конкретного товара",
)
async def delete_all_product_images(
    session: AsyncSessionDep,
    product_id: int,
):
    query = (
        select(Product)
        .options(joinedload(Product.images))
        .where(Product.id == product_id)
    )
    result = await session.execute(query)
    product = result.scalar()

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    if not product.images:
        raise HTTPException(status_code=404, detail="No images found for this product")

    # Удаляем файлы с диска
    for image in product.images:
        image_path = Path(image.image_path)
        if image_path.exists():
            image_path.unlink()

    # Удаляем записи из базы данных
    await session.execute(
        delete(ProductImage).where(ProductImage.product_id == product_id)
    )
    await session.commit()

    return {"message": "All images deleted successfully"}


@router.delete(
    "/{product_id}/{image_id}",
    summary="Удалить одно изображение товара",
    description="Удаляет конкретное изображение товара по ID",
)
async def delete_one_product_image(
    session: AsyncSessionDep,
    product_id: int,
    image_id: int,
):
    exists_product = await session.scalar(
        select(exists().where(Product.id == product_id))
    )
    if not exists_product:
        raise HTTPException(status_code=404, detail="Product not found")

    query = select(ProductImage).where(
        and_(ProductImage.id == image_id, ProductImage.product_id == product_id)
    )
    result = await session.execute(query)
    image = result.scalar()

    if not image:
        raise HTTPException(status_code=404, detail="Image not found")

    # Удаляем файл с диска
    image_path = Path(image.image_path)
    if image_path.exists():
        image_path.unlink()

    # Удаляем запись из базы данных
    # await session.execute(delete(ProductImage).where(ProductImage.id == image.id))
    await session.delete(image)
    await session.commit()

    return {"message": "Image deleted successfully"}
