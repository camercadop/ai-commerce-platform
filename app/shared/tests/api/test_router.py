import uuid
from typing import Any
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel

from app.shared.api.router import CRUDRouter

RESOURCE_ID = uuid.uuid4()


class _CreateSchema(BaseModel):
    name: str


class _UpdateSchema(BaseModel):
    name: str | None = None


class _ResponseSchema(BaseModel):
    id: uuid.UUID
    name: str


_STORED: dict[uuid.UUID, dict[str, Any]] = {}


def _create_fn(body: _CreateSchema, db: Any) -> dict[str, Any]:
    record = {"id": RESOURCE_ID, "name": body.name}
    _STORED[RESOURCE_ID] = record
    return record


def _get_fn(resource_id: uuid.UUID, db: Any) -> dict[str, Any]:
    return _STORED[resource_id]


def _update_fn(resource_id: uuid.UUID, data: dict[str, Any], db: Any) -> dict[str, Any]:
    _STORED[resource_id].update(data)
    return _STORED[resource_id]


def _delete_fn(resource_id: uuid.UUID, db: Any) -> None:
    _STORED.pop(resource_id, None)


@pytest.fixture(autouse=True)
def reset_store() -> None:
    """Reset the in-memory store before each test."""
    _STORED.clear()
    _STORED[RESOURCE_ID] = {"id": RESOURCE_ID, "name": "original"}


@pytest.fixture
def db() -> MagicMock:
    """Return a mock database session."""
    return MagicMock()


@pytest.fixture
def client(db: MagicMock) -> TestClient:
    """Return a TestClient wired to a CRUDRouter with fake operations."""
    app = FastAPI()
    router = CRUDRouter(
        prefix="/items",
        response_model=_ResponseSchema,
        create_schema=_CreateSchema,
        update_schema=_UpdateSchema,
        get_db_dep=lambda: db,
        create_fn=_create_fn,
        get_fn=_get_fn,
        update_fn=_update_fn,
        delete_fn=_delete_fn,
    )
    app.include_router(router)
    return TestClient(app)


def test_create_returns_201(client: TestClient) -> None:
    response = client.post("/items", json={"name": "widget"})

    assert response.status_code == 201
    assert response.json()["name"] == "widget"


def test_create_commits(client: TestClient, db: MagicMock) -> None:
    client.post("/items", json={"name": "widget"})

    db.commit.assert_called_once()


def test_get_returns_200(client: TestClient) -> None:
    response = client.get(f"/items/{RESOURCE_ID}")

    assert response.status_code == 200
    assert response.json()["id"] == str(RESOURCE_ID)


def test_update_returns_200(client: TestClient) -> None:
    response = client.patch(f"/items/{RESOURCE_ID}", json={"name": "updated"})

    assert response.status_code == 200
    assert response.json()["name"] == "updated"


def test_update_commits(client: TestClient, db: MagicMock) -> None:
    client.patch(f"/items/{RESOURCE_ID}", json={"name": "updated"})

    db.commit.assert_called_once()


def test_update_excludes_unset_fields(client: TestClient) -> None:
    client.patch(f"/items/{RESOURCE_ID}", json={})

    assert _STORED[RESOURCE_ID]["name"] == "original"


def test_delete_returns_204(client: TestClient) -> None:
    response = client.delete(f"/items/{RESOURCE_ID}")

    assert response.status_code == 204


def test_delete_commits(client: TestClient, db: MagicMock) -> None:
    client.delete(f"/items/{RESOURCE_ID}")

    db.commit.assert_called_once()


def test_service_wiring_delegates_to_service_methods() -> None:
    """CRUDRouter with service= delegates create/get/update/delete to service instance methods."""
    mock_service_instance = MagicMock()
    mock_service_instance.create.return_value = {
        "id": RESOURCE_ID,
        "name": "from-service",
    }
    mock_service_instance.get.return_value = {"id": RESOURCE_ID, "name": "from-service"}
    mock_service_instance.update.return_value = {"id": RESOURCE_ID, "name": "updated"}
    mock_service_instance.delete.return_value = None

    mock_service_class = MagicMock(return_value=mock_service_instance)
    db = MagicMock()

    app = FastAPI()
    router = CRUDRouter(
        prefix="/items",
        response_model=_ResponseSchema,
        create_schema=_CreateSchema,
        update_schema=_UpdateSchema,
        get_db_dep=lambda: db,
        service=mock_service_class,
    )
    app.include_router(router)
    test_client = TestClient(app)

    test_client.post("/items", json={"name": "widget"})
    mock_service_instance.create.assert_called_once_with(name="widget")

    test_client.get(f"/items/{RESOURCE_ID}")
    mock_service_instance.get.assert_called_once_with(RESOURCE_ID)

    test_client.patch(f"/items/{RESOURCE_ID}", json={"name": "updated"})
    mock_service_instance.update.assert_called_once_with(
        RESOURCE_ID, {"name": "updated"}
    )

    test_client.delete(f"/items/{RESOURCE_ID}")
    mock_service_instance.delete.assert_called_once_with(RESOURCE_ID)
