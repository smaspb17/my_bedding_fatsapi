import asyncio
import os
import time
from collections import defaultdict
from pathlib import Path

import aiofiles
from aiohttp import ClientError

from fastapi import UploadFile, File, HTTPException, APIRouter
from fastapi_cache.decorator import cache
from markdown_it.rules_inline import image
from sqlalchemy import select, exists, delete, and_
from sqlalchemy.orm import joinedload

from app.core.config import settings
from app.db.database import AsyncSessionDep
from app.db.models.shop import ProductImage, Product
from app.s3_storage.client import s3_client
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

STORAGE_TYPE = settings.STORAGE_TYPE
BASE_FOLDER = Path(__file__).parent.parent.parent.parent / "media/products"


@router.get(
    "/{product_id}",
    summary="Получить все изображения товара",
    description="Получить все изображения товара",
    response_model=list[ImageView],
)
@cache(expire=60)
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

    # Фильтруем и сортируем по имени
    unique_files = {file.filename: file for file in files}
    sorted_files = sorted(unique_files.items(), key=lambda x: x[0])
    filenames, files = zip(*sorted_files) if sorted_files else ([], [])

    # Формируем пути для хранения файлов
    image_paths = [
        (BASE_FOLDER / str(product_id) / name) if STORAGE_TYPE == 'disk'
        else f"products/{product_id}/{name}"
        for name in filenames
    ]

    # Проверяем наличие аналогичных файлов (по именам) в БД
    existing_images = await session.scalars(
        select(ProductImage.image_path)
        .where(ProductImage.product_id == product_id, ProductImage.image_path.in_(image_paths))
    )
    existing_images = existing_images.all()
    if existing_images:
        raise HTTPException(
            status_code=400,
            detail=f"Картинки уже загружены: {', '.join(existing_images)}"
        )

    # Асинхронное сохранение файлов
    async def save_file(file: UploadFile, image_path: str, client1) -> ProductImage:
        if STORAGE_TYPE == 'disk':
            product_folder = BASE_FOLDER / str(product_id)
            product_folder.mkdir(parents=True, exist_ok=True)
            # Записываем файл на диск
            async with aiofiles.open(image_path, "wb") as buffer:
                await buffer.write(await file.read())
        else:
            await s3_client.upload_file(file, image_path, client1)

        return ProductImage(product_id=product_id, image_path=image_path)

    start = time.perf_counter()
    async with s3_client.get_client() as client:
        tasks = [save_file(file, path, client) for file, path in zip(files, image_paths)]
        saved_images = await asyncio.gather(*tasks)
        # for task in tasks:
        #     await task
    end = time.perf_counter()
    print(f'Время загрузки файлов составило {end - start:.2f}')

    session.add_all(saved_images)
    await session.commit()
    return [{'filename': filename, 'image_path': image_path}
            for filename, image_path in zip(filenames, image_paths)]


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

    if STORAGE_TYPE == 'disk':
        # Удаляем файлы с диска
        for image in product.images:
            image_path = Path(image.image_path)
            if image_path.exists():
                image_path.unlink()

    else:
        keys = [image.image_path for image in product.images]
        print(keys)
        start = time.perf_counter()
        async with s3_client.get_client() as client:
            await s3_client.delete_all_files(keys, client)
        end = time.perf_counter()
        print(f'Время удаления файлов составило {end - start}')

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

    if STORAGE_TYPE == 'disk':
        # Удаляем файл с диска
        image_path = Path(image.image_path)
        if image_path.exists():
            image_path.unlink()
    else:
        await s3_client.delete_one_file(image.image_path)

    # Удаляем запись из базы данных
    # await session.execute(delete(ProductImage).where(ProductImage.id == image.id))
    await session.delete(image)
    await session.commit()

    return {"message": "Image deleted successfully"}


# @router.put(
#     "/{product_id}/{image_id}",
#     summary="Обновить изображение товара",
#     description="Заменяет конкретное изображение товара новым файлом",
# )
# async def update_product_image(
#     session: AsyncSessionDep,
#     product_id: int,
#     image_id: int,
#     file: UploadFile = File(...),
# ):
#     # проверка наличия товара
#     exists_product = await session.scalar(
#         select(exists().where(Product.id == product_id))
#     )
#     if not exists_product:
#         raise HTTPException(status_code=404, detail="Product not found")
#     # получение и проверка наличия файла с картинкой
#     query = select(ProductImage).where(
#         ProductImage.id == image_id, ProductImage.product_id == product_id
#     )
#     result = await session.execute(query)
#     image = result.scalar()
#     if not image:
#         raise HTTPException(status_code=404, detail="Image not found")
#
#     # Удаляем старый файл
#     old_image_path = Path(image.image_path)
#     if old_image_path.exists():
#         old_image_path.unlink()
#
#     # Сохраняем новый файл
#     product_folder = Path(UPLOAD_FOLDER) / str(product_id)
#     product_folder.mkdir(parents=True, exist_ok=True)
#     new_file_location = product_folder / file.filename
#     async with aiofiles.open(new_file_location, "wb") as buffer:
#         await buffer.write(await file.read())
#
#     # Обновляем запись в БД
#     image.image_path = str(new_file_location)
#     await session.commit()
#
#     return {
#         "message": "Image updated successfully",
#         "new_image_path": str(new_file_location),
#     }