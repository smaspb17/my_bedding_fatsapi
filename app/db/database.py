import logging
import re
from typing import Annotated

from fastapi import Depends
from sqlmodel import SQLModel
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings


# class SQLQueryFormatter(logging.Formatter):
#     def __init__(self):
#         super().__init__()
#
#     def format(self, record):
#         message = record.getMessage()
#
#         # Убираем ненужные флаги кэша и параметры
#         if "cached" in message or message in ["BEGIN", "COMMIT", "ROLLBACK"]:
#             return f"{message}\n"  # Сохранить пустую строку после BEGIN, COMMIT, ROLLBACK и кэша
#
#         # Если это SQL-запрос, добавляем пустую строку после запроса
#         if re.search(r"\b(SELECT|INSERT|UPDATE|DELETE|CREATE|DROP|ALTER)\b", message, re.IGNORECASE):
#             message = re.sub(r"\[cached since .*? ago\] ", "", message)  # Убираем кэш
#             return f"{message}\n"  # Добавляем пустую строку после SQL-запроса
#
#         # Проверяем параметры запроса (например, (1,), (5, 0))
#         if re.match(r"^\(\d+(,\s*\d+)*\)$", message):
#             return f"{message}\n"  # Параметры в скобках, добавляем пустую строку после
#
#         # Для всех остальных случаев (например, INFO сообщения)
#         return f"{message}\n"  # Добавляем пустую строку
#
# # 🔹 Настроим логирование SQLAlchemy
# sqlalchemy_logger = logging.getLogger("sqlalchemy.engine.Engine")
# sqlalchemy_logger.setLevel(logging.INFO)  # Логируем только SQL
#
# # 🔹 Добавляем кастомный обработчик логов
# handler = logging.StreamHandler()
# handler.setFormatter(SQLQueryFormatter())
#
# # 🔹 Очищаем старые обработчики и добавляем новый
# sqlalchemy_logger.handlers.clear()
# sqlalchemy_logger.addHandler(handler)




DATABASE_URL = settings.DATABASE_URL

# Создаём асинхронный движок
engine = create_async_engine(DATABASE_URL, echo=True)

# Создаём фабрику сессий. Отменена просрочка объектов!!!
async_session_maker = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


# Функция для создания базы данных и таблиц
async def create_db_and_tables():
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)


# Асинхронный генератор сессий для зависимостей FastAPI
async def get_session() -> AsyncSession:
    async with async_session_maker() as session:
        print(f'Создана сессия {session}')
        yield session


AsyncSessionDep = Annotated[AsyncSession, Depends(get_session)]
