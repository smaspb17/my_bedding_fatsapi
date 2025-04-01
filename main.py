from typing import Annotated

import asyncio
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends
from enum import Enum

from fastapi.exceptions import RequestValidationError

from app import auth
from app.auth.endpoints import get_current_user, User
# from app.auth.security import AuthCredsDep
from app.auth.security import oauth2_scheme
from app.core.config import settings

from app.shop.endpoints import categories, products, tags, images
from app.db import fixtures
from app.core.handlers import (
    custom_request_validation_exception_handler,
)
from app.db.database import create_db_and_tables, engine
from app.admin.admin_config import init_admin

# импорты кэширования
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
from fastapi_cache.decorator import cache

from redis import asyncio as aioredis
# import logging
#
# logging.basicConfig(level=logging.DEBUG)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    # await create_db_and_tables()  # НЕ НУЖЕН, использую alembic
    # Клиент для кеширования
    cache_redis = aioredis.from_url(settings.REDIS_URL)  # Подключение к Redis
    # Инициализация кэша
    FastAPICache.init(RedisBackend(cache_redis), prefix="fastapi-cache")  # Инициализация кэша
    # init админки
    init_admin(_app, engine)
    # Передаем Redis клиент в зависимости
    yield
    # Закрываем соединения при завершении
    await cache_redis.close()


app = FastAPI(
    title="Интернет-магазин MyBedding",
    version="0.1",
    contact={
        "name": "Техподдержка",
        "email": "smaspb17@gmail.com",
    },
    lifespan=lifespan,
)
app.include_router(categories.router)
app.include_router(products.router)
app.include_router(fixtures.router)
app.include_router(tags.router)
app.include_router(images.router)
app.include_router(auth.endpoints.router)
app.add_exception_handler(
    RequestValidationError, custom_request_validation_exception_handler
)


class Tags(Enum):
    home = "Главная страница"
    shop = "Магазин"
    products = "Товары"
    cart = "Корзина"


@app.get(
    "/",
    tags=[Tags.home],
    summary="Главная страница сайта",
    description="Получение контекста главной страницы супер-пупер-мега сайта MyBedding",
    response_description="Успешный ответ на запрос главной страницы",
)
@cache(expire=10)
async def home(
        # credentials: AuthCredsDep,
        current_user: Annotated[User, Depends(get_current_user)]
):
    # """
    # Create an item with all the information:
    # - **name**: each item must have a name
    # - **description**: a long description
    # - **price**: required
    # - **tax**: if the item doesn't have tax, you can omit this
    # - **tags**: a set of unique tag strings for this item
    # """
    start = time.perf_counter()
    await asyncio.sleep(3)
    end = time.perf_counter()
    diff_time = end - start
    print(f"{diff_time:.2f}")
    return {"message": "Это главная страница"}
