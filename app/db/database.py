from typing import Annotated

from fastapi import Depends
from sqlmodel import SQLModel
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.db.models.base import Base


# Создаём асинхронный движок
engine = create_async_engine(settings.DATABASE_URL_asyncpg, echo=True)


# Создаём фабрику сессий. Отменены отсоединение объектов
# и новые запросы к базе данных после каждого .commit()
async_session_maker = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


# Функция для создания базы данных и таблиц
# не нужен-использую alembic
async def create_db_and_tables():
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.drop_all)
        await conn.run_sync(SQLModel.metadata.create_all)
        # из declarative_base()
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)


# Асинхронный генератор сессий для зависимостей FastAPI
async def get_session() -> AsyncSession:
    async with async_session_maker() as session:
        print(f"Создана сессия {session}")
        yield session


AsyncSessionDep = Annotated[AsyncSession, Depends(get_session)]
