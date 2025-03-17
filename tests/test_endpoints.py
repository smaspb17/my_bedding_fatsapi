import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, create_engine, SQLModel, text
from sqlmodel.pool import StaticPool

from app.db.database import get_session
from app.db.models.shop import Category
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


@pytest.fixture(name="client")
def client_fixture(session: Session):
    def get_session_override():
        return session

    app.dependency_overrides[get_session] = get_session_override
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


def test_home_success(client: TestClient):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Это главная страница"}


def test_not_found_error(client: TestClient):
    response = client.get('/non_existing_path')
    assert response.status_code == 404
    assert response.json() == {"detail": "Not Found"}


def test_get_category_list_success(session: Session, client: TestClient):
    cat1 = Category(title="Тестовый1", description="Тестовый1")
    cat2 = Category(title="Тестовый2", description="Тестовый2")
    session.add_all([cat1, cat2])
    session.commit()
    response = client.get("/catalog")
    assert response.status_code == 200
    assert response.json() == [
        {"title": "Тестовый1", "description": "Тестовый1", "id": 1},
        {"title": "Тестовый2", "description": "Тестовый2", "id": 2},
    ]


def test_category_create_success(session: Session, client: TestClient):
    response = client.post(
        "/catalog", json={"title": "Тестовый", "description": "Тестовый"}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["id"] == 1
    assert data["title"] == "Тестовый"
    assert data["description"] == "Тестовый"


def test_category_create_missing_title(session: Session, client: TestClient):
    response = client.post(
        "/catalog", json={"description": "Тестовый"}
    )
    assert response.status_code == 400
    data = response.json()
    assert len(data['detail']) > 0
    assert data["detail"][0]["loc"] == ["body", "title"]
    assert data["detail"][0]["msg"] == "Field required"


def test_category_create_missing_description(session: Session, client: TestClient):
    response = client.post(
        "/catalog", json={"title": "Тестовый"}
    )
    assert response.status_code == 400
    data = response.json()
    assert len(data['detail']) > 0
    assert data["detail"][0]["loc"] == ["body", "description"]
    assert data["detail"][0]["msg"] == "Field required"










# def test_create_cat_title_unique_constraint(client: TestClient):
#     client.post("/catalog", json={"title": "Уникум", "description": "string"})
#     response = client.post(
#         "/catalog", json={"title": "Уникум", "description": "string"}
#     )
#     assert response.status_code == 400
#     assert response.json() == {
#         "detail": "Category is already exists. Unique constraint failed: title field"
#     }


# def test_read_hero(session: Session, client: TestClient):
#     hero_1 = Hero(name="Deadpond", secret_name="Dive Wilson")
#     session.add(hero_1)
#     session.commit()
#
#     response = client.get(f"/heroes/{hero_1.id}")
#     data = response.json()
#
#     assert response.status_code == 200
#     assert data["name"] == hero_1.name
#     assert data["secret_name"] == hero_1.secret_name
#     assert data["age"] == hero_1.age
#     assert data["id"] == hero_1.id
#
#
# def test_update_hero(session: Session, client: TestClient):
#     hero_1 = Hero(name="Deadpond", secret_name="Dive Wilson")
#     session.add(hero_1)
#     session.commit()
#
#     response = client.patch(f"/heroes/{hero_1.id}", json={"name": "Deadpuddle"})
#     data = response.json()
#
#     assert response.status_code == 200
#     assert data["name"] == "Deadpuddle"
#     assert data["secret_name"] == "Dive Wilson"
#     assert data["age"] is None
#     assert data["id"] == hero_1.id
#
#
# def test_delete_hero(session: Session, client: TestClient):
#     hero_1 = Hero(name="Deadpond", secret_name="Dive Wilson")
#     session.add(hero_1)
#     session.commit()
#
#     response = client.delete(f"/heroes/{hero_1.id}")
#
#     hero_in_db = session.get(Hero, hero_1.id)
#
#     assert response.status_code == 200
#
#     assert hero_in_db is None
