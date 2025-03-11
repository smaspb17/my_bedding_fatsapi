from fastapi import FastAPI
from enum import Enum

from fastapi.exceptions import RequestValidationError

from app.api.endpoints import fixtures
from app.api.endpoints.shop import categories, products, tags
from app.core.handlers import custom_request_validation_exception_handler
from app.db.database import create_db_and_tables

app = FastAPI(
    title="Интернет-магазин MyBedding",
    version="0.1",
    contact={
        "name": "Техподдержка",
        "email": "smaspb17@gmail.com",
    },
)
app.include_router(categories.router)
app.include_router(products.router)
app.include_router(fixtures.router)
app.include_router(tags.router)
app.add_exception_handler(
    RequestValidationError, custom_request_validation_exception_handler
)


@app.on_event("startup")
def on_startup():
    create_db_and_tables()


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
async def home():
    # """
    # Create an item with all the information:
    # - **name**: each item must have a name
    # - **description**: a long description
    # - **price**: required
    # - **tax**: if the item doesn't have tax, you can omit this
    # - **tags**: a set of unique tag strings for this item
    # """
    return {"message": "Это главная страница"}
