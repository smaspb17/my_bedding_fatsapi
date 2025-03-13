import pytest
from sqlmodel import Session, create_engine, SQLModel, text
from sqlmodel.pool import StaticPool

from main import app

sqlite_file_name = "testing.db"
# sqlite_url = f'sqlite:///{sqlite_file_name}'
sqlite_url = "sqlite://"  # int-memory tests


@pytest.fixture(name="session")
def session_fixture():
    # создание движка in-memory
    engine = create_engine(
        sqlite_url,
        connect_args={"check_same_thread": False},
        echo=True,
        poolclass=StaticPool,
    )
    # создание таблиц в БД
    SQLModel.metadata.create_all(engine)
    # добавим в sqlite поддержку FK
    with engine.connect() as connection:
        connection.execute(text("PRAGMA foreign_keys=ON"))
    with Session(engine) as session:
        yield session




# app.dependency_overrides[get_session] = get_session_override
