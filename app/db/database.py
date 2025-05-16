import logging
from typing import Annotated, AsyncGenerator

from fastapi import Depends
from sqlmodel import SQLModel
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    create_async_engine,
    async_sessionmaker,
)

from app.core.config import settings
from app.db.models.base import Base

logger = logging.getLogger(__name__)

# Создаём асинхронный движок
engine = create_async_engine(
    settings.DATABASE_URL_asyncpg,
    echo=False,
    pool_size=10,           # базовый размер пула
    max_overflow=20,        # дополнительные соединения при нагрузке
    pool_timeout=30,        # время ожидания (сек)
    pool_recycle=3600,      # пересоздавать соединения каждые 3600 сек (1 час)
)


# Создаём фабрику сессий. Отменены отсоединение объектов
# и новые запросы к базе данных после каждого .commit()
async_session_maker = async_sessionmaker(bind=engine, expire_on_commit=False)


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
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        # logger.info(f"Создана сессия {session}")
        yield session


AsyncSessionDep = Annotated[AsyncSession, Depends(get_session)]
