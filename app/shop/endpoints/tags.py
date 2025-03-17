from fastapi import APIRouter, HTTPException
from sqlmodel import select, exists

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
async def tag_create(session: AsyncSessionDep) -> list[TagView]:
    result = await session.execute(select(Tag))
    tags = result.scalars().all()
    return tags


@router.post(
    "/create",
    summary="Создание тега",
    description="Создание тега",
    response_model=TagView,
    status_code=201,
)
async def tag_create(tag: TagCreate, session: AsyncSessionDep) -> TagView:
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
    return TagView.from_orm(tag_db)


@router.patch(
    "/update/{tag_id}",
    summary="Частичное обновление тега",
    description="Частичное обновление тега",
    response_model=TagView,
)
async def tag_update(tag_id: int, tag: TagUpdate, session: AsyncSessionDep) -> TagView:
    tag_db = await session.get(Tag, tag_id)
    if not tag_db:
        raise HTTPException(
            status_code=404,
            detail=f"Tag with id={tag_id} not found. Please check the tag ID and try again.",
        )
    is_exists = await session.scalar(select(exists().where(Tag.name == tag.name, Tag.id != tag_id)))
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
    return TagView.from_orm(tag_db)


@router.delete(
    "/delete/{tag_id}",
    summary="Удаление тега",
    description="Удаление тега",
    response_model=TagView,
)
async def tag_delete(tag_id: int, session: AsyncSessionDep) -> TagView:
    tag = await session.get(Tag, tag_id)
    if not tag:
        raise HTTPException(
            status_code=404,
            detail=f"Tag with id={tag_id} not found. Please check the tag ID and try again.",
        )
    await session.delete(tag)
    await session.commit()
    return TagView.from_orm(tag)



