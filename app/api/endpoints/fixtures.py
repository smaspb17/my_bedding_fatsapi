import json
import importlib
import inspect
from datetime import datetime
from pathlib import Path
from enum import Enum
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlmodel import SQLModel, Session, select
from app.db.database import get_session

router = APIRouter(
    prefix="/fixtures",
    tags=["Фикстуры"],
)

EXPORT_PATH = Path(r"D:\Интернет-магазин\FastAPI\fixtures")
EXPORT_PATH.mkdir(parents=True, exist_ok=True)  # Создаём папку, если её нет

# Список модулей, в которых хранятся модели
MODEL_MODULES = [
    "app.db.shop.models",
    # "app.db.order .models",
]

# Кеш списка моделей (обновляется только при изменении структуры БД)
CACHED_MODELS = {}


def discover_models():
    """Функция ищет все модели с __table__ во всех модулях из MODEL_MODULES."""
    print("Вызов функции discover_models - поиск списка моделей БД")
    global CACHED_MODELS
    models_dict = {}

    for module_path in MODEL_MODULES:
        try:
            module = importlib.import_module(module_path)  # Импортируем модуль
            for name, obj in inspect.getmembers(module):  # Получаем атрибуты модуля
                if (
                    inspect.isclass(obj)
                    and hasattr(obj, "__table__")
                    and issubclass(obj, SQLModel)
                ):
                    models_dict[name.lower()] = (
                        obj  # Сохраняем в формате { "productdb": ProductDB }
                    )
        except Exception as e:
            print(f"Ошибка при загрузке модуля {module_path}: {e}")

    CACHED_MODELS = models_dict  # Кешируем найденные модели
    return models_dict


# Выполняем поиск моделей при загрузке сервера
discover_models()


class ModelNameEnum(str, Enum):
    """Динамический Enum для выпадающего списка моделей."""

    @classmethod
    def _missing_(cls, value):
        raise ValueError(
            f"Модель '{value}' не найдена. Выберите из: {list(CACHED_MODELS.keys())}"
        )


# Создаём Enum из кеша
ModelNameEnum = Enum(
    "ModelNameEnum", {name.upper(): name for name in CACHED_MODELS.keys()}
)


@router.get(
    "/export/{model_name}",
    summary="🛑 Выгрузка фикстур в файл. ❗❗Сперва проверь базу данных❗❗",
)
def export_data(model_name: ModelNameEnum, session: Session = Depends(get_session)):
    """
    Создание json-файла с фикстурами модели БД.
    - Выбери модель БД, из которой будут выгружены данные в одноименный json-файл.
    - Адрес создания файла указан в fixtures.py.
    - Модели в выпадающий список добавляются автоматически.
    """
    model_db = CACHED_MODELS.get(model_name.value)
    if not model_db:
        raise HTTPException(status_code=400, detail="Модель не найдена")

    objects = session.exec(select(model_db)).unique().all()

    file_path = EXPORT_PATH / f"{model_name.value}.json"
    with file_path.open("w", encoding="utf-8") as f:
        json.dump(
            {model_name.value: [obj.model_dump(mode="json") for obj in objects]},
            f,
            ensure_ascii=False,
            indent=2,
        )

    return {"message": f"Данные успешно выгружены в {file_path}"}


@router.post("/import/{model_name}", summary="Загрузка фикстур в базу данных")
def import_data(model_name: ModelNameEnum, session: Session = Depends(get_session)):
    """
    Загрузка фикстур базы данных из json-файла.
    - ❗ Перед загрузкой из файла, данные в БД из указанной модели будут удалены.
    - Выбери модель БД, в которую будут выгружены данные из одноименного json-файла.
    - Адрес нахождения файла указан в fixtures.py.
    - Модели в выпадающий список добавляются автоматически.
    """
    model_db = CACHED_MODELS.get(model_name.value)
    if not model_db:
        raise HTTPException(status_code=400, detail="Модель не найдена")

    file_path = EXPORT_PATH / f"{model_name.value}.json"
    if not file_path.exists():
        raise HTTPException(status_code=400, detail="Файл с данными не найден")

    with file_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    # Очистить таблицу перед загрузкой данных
    try:
        session.execute(text("PRAGMA foreign_keys = OFF;"))  # Отключаем проверки FK
        session.query(model_db).delete()
        session.commit()
    except Exception as e:
        session.rollback()
        raise HTTPException(
            status_code=500, detail=f"Ошибка при очистке таблицы: {str(e)}"
        )

    def parse_datetime(item):
        if "created" in item:
            item["created"] = datetime.fromisoformat(item["created"])
        if "updated" in item:
            item["updated"] = datetime.fromisoformat(item["updated"])
        return item

    objects = [
        model_db(**parse_datetime(item)) for item in data.get(model_name.value, [])
    ]

    try:
        session.add_all(objects)
        session.commit()
    except IntegrityError as e:
        session.rollback()
        return JSONResponse(
            status_code=400, content={"detail": "Integrity error", "error": str(e)}
        )
    finally:
        session.execute(text("PRAGMA foreign_keys = ON;"))  # Включаем проверки FK обратно

    return {"message": f"Данные из {file_path} успешно загружены в базу"}
