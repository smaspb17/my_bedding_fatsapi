from typing import Annotated

import asyncio
from fastapi import APIRouter, HTTPException, Security
from fastapi_cache.decorator import cache
from sqlmodel import select, exists

from app.auth.schemas import TokenData
from app.auth.security import has_permissions
from app.shop.schemas.error_schemas import (
    BadRequestErrorSchema,
    NotFoundErrorSchema,
)
from app.shop.schemas.tags import TagView, TagCreate, TagUpdate
from app.db.database import AsyncSessionDep
from app.db.models.shop import Tag

router = APIRouter(
    prefix="/tags",
    tags=["Магазин: Теги"],
    responses={
        400: {"model": BadRequestErrorSchema, "description": "Bad Request"},
        404: {"model": NotFoundErrorSchema, "description": "Not Found"},
    },
)


@router.get(
    "/",
    summary="Получение списка тегов",
    description="Получение списка тегов",
    response_model=list[TagView],
)
@cache(expire=60)
async def tag_create(
    _: Annotated[TokenData, Security(has_permissions, scopes=["shop:read"])],
    session: AsyncSessionDep,
) -> list[TagView]:
    result = await session.execute(select(Tag).order_by(Tag.id))
    tags = result.scalars().all()
    await asyncio.sleep(3)
    return tags


@router.post(
    "/create",
    summary="Создание тега",
    description="Создание тега",
    response_model=TagView,
    status_code=201,
)
async def tag_create(
    _: Annotated[TokenData, Security(has_permissions, scopes=["shop:create"])],
    session: AsyncSessionDep,
    tag: TagCreate,
) -> TagView:
    # stmt = select(exists().where(Tag.name == tag.name))
    # is_exists = session.exec(stmt).first()
    is_exists = await session.scalar(select(exists().where(Tag.name == tag.name)))
    if is_exists:
        raise HTTPException(
            status_code=404,
            detail="Tag is already exists. Unique constraint failed: name field",
        )
    # tag_db = Tag.model_validate(tag)
    tag_db = Tag(**tag.model_dump())
    session.add(tag_db)
    await session.commit()
    # session.refresh(tag_db)
    return TagView.model_validate(tag_db)


@router.patch(
    "/update/{tag_id}",
    summary="Частичное обновление тега",
    description="Частичное обновление тега",
    response_model=TagView,
)
async def tag_update(
    _: Annotated[TokenData, Security(has_permissions, scopes=["shop:update"])],
    session: AsyncSessionDep,
    tag_id: int,
    tag: TagUpdate,
) -> TagView:
    tag_db = await session.get(Tag, tag_id)
    if not tag_db:
        raise HTTPException(
            status_code=404,
            detail=f"Tag with id={tag_id} not found. Please check the tag ID and try again.",
        )
    is_exists = await session.scalar(
        select(exists().where(Tag.name == tag.name, Tag.id != tag_id))
    )
    if is_exists:
        raise HTTPException(
            status_code=404,
            detail="Tag is already exists. Unique constraint failed: name field",
        )
    # data = tag.model_dump(exclude_unset=True).items()
    # for field, value in data:
    #     setattr(tag_db, field, value)

    tag_data = tag.model_dump(exclude_unset=True).items()
    for field, value in tag_data:
        setattr(tag_db, field, value)
    await session.commit()
    # session.refresh(tag_db)
    return TagView.model_validate(tag_db)


@router.delete(
    "/delete/{tag_id}",
    summary="Удаление тега",
    description="Удаление тега",
    response_model=TagView,
)
async def tag_delete(
    _: Annotated[TokenData, Security(has_permissions, scopes=["shop:delete"])],
    session: AsyncSessionDep,
    tag_id: int,
) -> TagView:
    tag = await session.get(Tag, tag_id)
    if not tag:
        raise HTTPException(
            status_code=404,
            detail=f"Tag with id={tag_id} not found. Please check the tag ID and try again.",
        )
    await session.delete(tag)
    await session.commit()
    return TagView.model_validate(tag)
