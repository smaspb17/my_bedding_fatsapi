# main.py
from typing import Annotated
import logging
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, Request
from enum import Enum

from fastapi.exceptions import RequestValidationError

from app.auth.endpoints import get_current_user, User

from app.core.config import settings


from app.shop.endpoints import categories, products, tags, images
from app.auth.endpoints import router as auth_router
from app.db import fixtures
from app.core.handlers import (
    custom_request_validation_exception_handler,
)
from app.db.database import engine
from app.admin.admin_config import init_admin


# импорты кэширования
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
from fastapi_cache.decorator import cache

from redis import asyncio as aioredis


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    from app.logging.logger import configure_logging

    configure_logging()
    logger.info("Logging configuration completed")
    # Инициализация логирования (первая строка!)
    cache_redis = aioredis.from_url(settings.REDIS_URL)  # Подключение к Redis
    FastAPICache.init(RedisBackend(cache_redis), prefix="fastapi-cache")
    logger.info("Redis cache initialized")

    init_admin(_app, engine)
    logger.info("Admin initialization completed")
    yield
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
# app.include_router(users.router)
app.include_router(auth_router)
app.add_exception_handler(
    RequestValidationError, custom_request_validation_exception_handler
)


logger = logging.getLogger(__name__)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.perf_counter()
    response = await call_next(request)
    process_time = time.perf_counter() - start_time
    logger.info(
        f"Время выполнения запроса {request.url.path}: {process_time:.4f} сек."
    )
    return response


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
    current_user: Annotated[User, Depends(get_current_user)],
):
    # """
    # Create an item with all the information:
    # - **name**: each item must have a name
    # - **description**: a long description
    # - **price**: required
    # - **tax**: if the item doesn't have tax, you can omit this
    # - **tags**: a set of unique tag strings for this item
    # """
    logger.info("Вызов главной страницы")
    return {"message": "Это главная страница"}
