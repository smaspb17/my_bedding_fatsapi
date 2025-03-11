from fastapi import APIRouter, HTTPException
from sqlmodel import select, exists, and_

from app.api.schemas.shop.error_schemas import (
    BadRequestErrorSchema,
    NotFoundErrorSchema,
)
from app.api.schemas.shop.tags import TagView, TagCreate, TagUpdate
from app.db.database import SessionDep
from app.db.shop.models import TagDB

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
def tag_create(session: SessionDep) -> list[TagView]:
    tags = session.exec(select(TagDB)).all()
    return tags


@router.post(
    "/create",
    summary="Создание тега",
    description="Создание тега",
    response_model=TagView,
)
def tag_create(tag: TagCreate, session: SessionDep) -> TagView:
    stmt = select(exists().where(TagDB.name == tag.name))
    is_exists = session.exec(stmt).first()
    if is_exists:
        raise HTTPException(
            status_code=404,
            detail="Tag is already exists. Unique constraint failed: name field",
        )
    tag_db = TagDB(**tag.model_dump())
    session.add(tag_db)
    session.commit()
    session.refresh(tag_db)
    return TagView(**tag_db.model_dump())


@router.patch(
    "/update/{tag_id}",
    summary="Частичное обновление тега",
    description="Частичное обновление тега",
    response_model=TagView,
)
def tag_update(tag_id: int, tag: TagUpdate, session: SessionDep) -> TagView:
    tag_db = session.get(TagDB, tag_id)
    if not tag_db:
        raise HTTPException(
            status_code=404,
            detail=f"Tag with id={tag_id} not found. Please check the tag ID and try again.",
        )
    stmt = select(exists().where(and_(TagDB.name == tag.name, TagDB.id != tag_id)))
    is_exists = session.exec(stmt).first()
    if is_exists:
        raise HTTPException(
            status_code=404,
            detail="Tag is already exists. Unique constraint failed: name field",
        )
    data = tag.model_dump(exclude_unset=True).items()
    print(f"data {data}")
    for field, value in data:
        setattr(tag_db, field, value)
    session.commit()
    session.refresh(tag_db)
    return TagView(**tag_db.model_dump())


@router.delete(
    "/delete/{tag_id}",
    summary="Удаление тега",
    description="Удаление тега",
    response_model=TagView,
)
def tag_delete(tag_id: int, session: SessionDep) -> TagView:
    tag = session.get(TagDB, tag_id)
    if not tag:
        raise HTTPException(
            status_code=404,
            detail=f"Tag with id={tag_id} not found. Please check the tag ID and try again.",
        )
    session.delete(tag)
    session.commit()
    return TagView(**tag.model_dump())



