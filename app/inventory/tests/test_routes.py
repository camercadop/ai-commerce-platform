import os
import uuid
from decimal import Decimal

from faker import Faker
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import update

from app.inventory.exceptions import InsufficientStock, InventoryItemAlreadyExists
from app.inventory.models import Reservation, ReservationStatus
from app.inventory.routes import PREFIX, register_exception_handlers
from app.inventory.schemas import (
    AdjustStockRequest,
    CreateInventoryItemRequest,
    InventoryItemResponse,
    ReserveStockRequest,
    ReservationResponse,
)
from app.shared.db import build_session_factory
from app.shared.events import MessageBroker

fake = Faker()


def make_create_inventory_item_payload(**kwargs: object) -> dict[str, object]:
    """Build a valid create-inventory-item request payload."""
    return {
        "variant_id": str(uuid.uuid4()),
        "initial_quantity": 10,
        **kwargs,
    }


def make_adjust_stock_payload(**kwargs: object) -> dict[str, object]:
    """Build a valid adjust-stock request payload."""
    return {
        "delta": 5,
        "note": "restock",
        **kwargs,
    }


def make_reserve_stock_payload(**kwargs: object) -> dict[str, object]:
    """Build a valid reserve-stock request payload."""
    return {
        "variant_id": str(uuid.uuid4()),
        "order_id": str(uuid.uuid4()),
        "quantity": 3,
        **kwargs,
    }


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


def test_health_returns_ok(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


# ---------------------------------------------------------------------------
# Inventory Items
# ---------------------------------------------------------------------------


def test_smoke_create_inventory_item(client: TestClient) -> None:
    response = client.post(
        PREFIX + "/items", json=make_create_inventory_item_payload()
    )

    assert response.status_code == 201


def test_create_inventory_item_returns_expected_body(client: TestClient) -> None:
    payload = make_create_inventory_item_payload()
    data = client.post(PREFIX + "/items", json=payload).json()

    assert data["variant_id"] == payload["variant_id"]
    assert data["quantity_on_hand"] == payload["initial_quantity"]
    assert data["quantity_reserved"] == 0
    assert data["quantity_available"] == payload["initial_quantity"]


def test_create_inventory_item_returns_409_when_already_exists(
    client: TestClient,
) -> None:
    payload = make_create_inventory_item_payload()
    client.post(PREFIX + "/items", json=payload)
    response = client.post(PREFIX + "/items", json=payload)

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "INVENTORY_ITEM_ALREADY_EXISTS"


def test_smoke_get_inventory(client: TestClient) -> None:
    payload = make_create_inventory_item_payload()
    item_id = client.post(PREFIX + "/items", json=payload).json()["id"]
    variant_id = payload["variant_id"]

    response = client.get(f"{PREFIX}/items/{variant_id}")

    assert response.status_code == 200


def test_get_inventory_returns_expected_body(client: TestClient) -> None:
    payload = make_create_inventory_item_payload()
    client.post(PREFIX + "/items", json=payload)
    variant_id = payload["variant_id"]

    data = client.get(f"{PREFIX}/items/{variant_id}").json()

    assert data["variant_id"] == variant_id
    assert data["quantity_on_hand"] == payload["initial_quantity"]
    assert data["quantity_reserved"] == 0
    assert data["quantity_available"] == payload["initial_quantity"]


def test_get_inventory_not_found_returns_404(client: TestClient) -> None:
    response = client.get(f"{PREFIX}/items/{uuid.uuid4()}")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "INVENTORY_ITEM_NOT_FOUND"


def test_smoke_adjust_stock(client: TestClient) -> None:
    payload = make_create_inventory_item_payload()
    client.post(PREFIX + "/items", json=payload)
    variant_id = payload["variant_id"]

    response = client.post(
        f"{PREFIX}/items/{variant_id}/adjust",
        json=make_adjust_stock_payload(),
    )

    assert response.status_code == 200


def test_adjust_stock_returns_expected_body(client: TestClient) -> None:
    payload = make_create_inventory_item_payload(initial_quantity=10)
    client.post(PREFIX + "/items", json=payload)
    variant_id = payload["variant_id"]

    data = client.post(
        f"{PREFIX}/items/{variant_id}/adjust",
        json={"delta": 5, "note": "restock"},
    ).json()

    assert data["quantity_on_hand"] == 15
    assert data["quantity_available"] == 15


def test_adjust_stock_not_found_returns_404(client: TestClient) -> None:
    response = client.post(
        f"{PREFIX}/items/{uuid.uuid4()}/adjust",
        json=make_adjust_stock_payload(),
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "INVENTORY_ITEM_NOT_FOUND"


def test_adjust_stock_insufficient_returns_400(client: TestClient) -> None:
    payload = make_create_inventory_item_payload(initial_quantity=5)
    client.post(PREFIX + "/items", json=payload)
    variant_id = payload["variant_id"]

    response = client.post(
        f"{PREFIX}/items/{variant_id}/adjust",
        json={"delta": -10, "note": "shrinkage"},
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVENTORY_INSUFFICIENT_STOCK"


# ---------------------------------------------------------------------------
# Reservations
# ---------------------------------------------------------------------------


def test_smoke_reserve_stock(client: TestClient) -> None:
    item_payload = make_create_inventory_item_payload()
    client.post(PREFIX + "/items", json=item_payload)

    response = client.post(
        PREFIX + "/reservations",
        json=make_reserve_stock_payload(variant_id=item_payload["variant_id"]),
    )

    assert response.status_code == 201


def test_reserve_stock_returns_expected_body(client: TestClient) -> None:
    item_payload = make_create_inventory_item_payload()
    client.post(PREFIX + "/items", json=item_payload)

    payload = make_reserve_stock_payload(variant_id=item_payload["variant_id"])
    data = client.post(PREFIX + "/reservations", json=payload).json()

    assert data["inventory_item_id"] is not None
    assert data["order_id"] == payload["order_id"]
    assert data["quantity"] == payload["quantity"]
    assert data["status"] == "reserved"


def test_reserve_stock_returns_existing_reservation(client: TestClient) -> None:
    item_payload = make_create_inventory_item_payload()
    client.post(PREFIX + "/items", json=item_payload)

    payload = make_reserve_stock_payload(variant_id=item_payload["variant_id"])
    first = client.post(PREFIX + "/reservations", json=payload).json()

    data = client.post(PREFIX + "/reservations", json=payload).json()

    assert data["id"] == first["id"]


def test_reserve_stock_not_found_returns_404(client: TestClient) -> None:
    response = client.post(
        PREFIX + "/reservations",
        json=make_reserve_stock_payload(),
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "INVENTORY_ITEM_NOT_FOUND"


def test_reserve_stock_insufficient_returns_400(client: TestClient) -> None:
    item_payload = make_create_inventory_item_payload(initial_quantity=2)
    client.post(PREFIX + "/items", json=item_payload)

    payload = make_reserve_stock_payload(
        variant_id=item_payload["variant_id"], quantity=5
    )
    response = client.post(PREFIX + "/reservations", json=payload)

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVENTORY_INSUFFICIENT_STOCK"


def test_smoke_release_reservation(client: TestClient) -> None:
    item_payload = make_create_inventory_item_payload()
    client.post(PREFIX + "/items", json=item_payload)
    reservation = client.post(
        PREFIX + "/reservations",
        json=make_reserve_stock_payload(variant_id=item_payload["variant_id"]),
    ).json()
    reservation_id = reservation["id"]

    response = client.post(f"{PREFIX}/reservations/{reservation_id}/release")

    assert response.status_code == 200


def test_release_reservation_returns_expected_body(client: TestClient) -> None:
    item_payload = make_create_inventory_item_payload()
    client.post(PREFIX + "/items", json=item_payload)
    reservation = client.post(
        PREFIX + "/reservations",
        json=make_reserve_stock_payload(variant_id=item_payload["variant_id"]),
    ).json()
    reservation_id = reservation["id"]

    data = client.post(f"{PREFIX}/reservations/{reservation_id}/release").json()

    assert data["status"] == "released"


def test_release_reservation_not_found_returns_404(client: TestClient) -> None:
    response = client.post(f"{PREFIX}/reservations/{uuid.uuid4()}/release")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "INVENTORY_RESERVATION_NOT_FOUND"


def test_release_reservation_confirmed_returns_400(client: TestClient) -> None:
    item_payload = make_create_inventory_item_payload()
    client.post(PREFIX + "/items", json=item_payload)
    reservation = client.post(
        PREFIX + "/reservations",
        json=make_reserve_stock_payload(variant_id=item_payload["variant_id"]),
    ).json()
    reservation_id = reservation["id"]

    session_factory = build_session_factory(os.environ["TEST_DATABASE_URL"])
    with session_factory() as session:
        session.execute(
            update(Reservation)
            .where(Reservation.id == reservation_id)
            .values(status=ReservationStatus.CONFIRMED)
        )
        session.commit()

    response = client.post(f"{PREFIX}/reservations/{reservation_id}/release")

    assert response.status_code == 400
    assert (
        response.json()["error"]["code"]
        == "INVENTORY_INVALID_RESERVATION_TRANSITION"
    )


def test_smoke_confirm_reservation(client: TestClient) -> None:
    item_payload = make_create_inventory_item_payload()
    client.post(PREFIX + "/items", json=item_payload)
    reservation = client.post(
        PREFIX + "/reservations",
        json=make_reserve_stock_payload(variant_id=item_payload["variant_id"]),
    ).json()
    reservation_id = reservation["id"]

    response = client.post(f"{PREFIX}/reservations/{reservation_id}/confirm")

    assert response.status_code == 200


def test_confirm_reservation_returns_expected_body(client: TestClient) -> None:
    item_payload = make_create_inventory_item_payload()
    client.post(PREFIX + "/items", json=item_payload)
    reservation = client.post(
        PREFIX + "/reservations",
        json=make_reserve_stock_payload(variant_id=item_payload["variant_id"]),
    ).json()
    reservation_id = reservation["id"]

    data = client.post(f"{PREFIX}/reservations/{reservation_id}/confirm").json()

    assert data["status"] == "confirmed"


def test_confirm_reservation_not_found_returns_404(client: TestClient) -> None:
    response = client.post(f"{PREFIX}/reservations/{uuid.uuid4()}/confirm")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "INVENTORY_RESERVATION_NOT_FOUND"


def test_confirm_reservation_released_returns_400(client: TestClient) -> None:
    item_payload = make_create_inventory_item_payload()
    client.post(PREFIX + "/items", json=item_payload)
    reservation = client.post(
        PREFIX + "/reservations",
        json=make_reserve_stock_payload(variant_id=item_payload["variant_id"]),
    ).json()
    reservation_id = reservation["id"]

    session_factory = build_session_factory(os.environ["TEST_DATABASE_URL"])
    with session_factory() as session:
        session.execute(
            update(Reservation)
            .where(Reservation.id == reservation_id)
            .values(status=ReservationStatus.RELEASED)
        )
        session.commit()

    response = client.post(f"{PREFIX}/reservations/{reservation_id}/confirm")

    assert response.status_code == 400
    assert (
        response.json()["error"]["code"]
        == "INVENTORY_INVALID_RESERVATION_TRANSITION"
    )
