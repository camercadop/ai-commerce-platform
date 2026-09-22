import uuid
from decimal import Decimal
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.orders.adapters import StubCartPort
from app.orders.exceptions import CartHasNoItems
from app.orders.ports import CartData
from app.orders.routes import register_exception_handlers
from app.orders.tests.fakes import make_cart_data, make_cart_item_data


def make_place_order_payload(**kwargs: object) -> dict[str, object]:
    """Build a valid place-order request payload with randomised defaults."""
    return {
        "cart_id": str(uuid.uuid4()),
        **kwargs,
    }


def _active_cart_with_item() -> CartData:
    """Return a minimal active cart with one item for route-level tests."""
    return make_cart_data(
        items=[make_cart_item_data(unit_price="10.00", quantity=1)],
    )


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


def test_health_returns_ok(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


# ---------------------------------------------------------------------------
# POST /api/v1/orders
# ---------------------------------------------------------------------------


def test_smoke_place_order(client: TestClient) -> None:
    with patch.object(StubCartPort, "get_cart", return_value=_active_cart_with_item()):
        response = client.post(
            "/api/v1/orders", json=make_place_order_payload()
        )

    assert response.status_code == 201


def test_place_order_returns_expected_body(client: TestClient) -> None:
    cart = _active_cart_with_item()
    with patch.object(StubCartPort, "get_cart", return_value=cart):
        data = client.post(
            "/api/v1/orders", json=make_place_order_payload(cart_id=str(cart["id"]))
        ).json()

    assert data["cart_id"] == str(cart["id"])
    assert data["status"] == "pending"
    assert data["subtotal"] == "10.00"
    assert data["total_amount"] == "10.00"
    assert len(data["items"]) == 1
    assert data["adjustments"] == []


def test_place_order_returns_400_when_cart_not_found(client: TestClient) -> None:
    with patch.object(StubCartPort, "get_cart", return_value=None):
        response = client.post(
            "/api/v1/orders", json=make_place_order_payload()
        )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "ORDER_CART_INVALID_REFERENCE"


def test_place_order_returns_400_when_cart_not_active(client: TestClient) -> None:
    cart = make_cart_data(status="checked_out", items=[make_cart_item_data()])
    with patch.object(StubCartPort, "get_cart", return_value=cart):
        response = client.post(
            "/api/v1/orders", json=make_place_order_payload()
        )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "ORDER_CART_NOT_ELIGIBLE"


def test_place_order_returns_400_when_cart_has_no_items(client: TestClient) -> None:
    cart = make_cart_data(items=[])
    with patch.object(StubCartPort, "get_cart", return_value=cart):
        response = client.post(
            "/api/v1/orders", json=make_place_order_payload()
        )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "ORDER_CART_HAS_NO_ITEMS"


# ---------------------------------------------------------------------------
# GET /api/v1/orders/{order_id}
# ---------------------------------------------------------------------------


def test_smoke_get_order(client: TestClient) -> None:
    with patch.object(StubCartPort, "get_cart", return_value=_active_cart_with_item()):
        order_id = client.post(
            "/api/v1/orders", json=make_place_order_payload()
        ).json()["id"]

    response = client.get(f"/api/v1/orders/{order_id}")

    assert response.status_code == 200


def test_get_order_returns_expected_body(client: TestClient) -> None:
    cart = _active_cart_with_item()
    with patch.object(StubCartPort, "get_cart", return_value=cart):
        order_id = client.post(
            "/api/v1/orders", json=make_place_order_payload(cart_id=str(cart["id"]))
        ).json()["id"]

    data = client.get(f"/api/v1/orders/{order_id}").json()

    assert data["id"] == order_id
    assert data["status"] == "pending"
    assert "items" in data
    assert "adjustments" in data


def test_get_order_not_found_returns_404(client: TestClient) -> None:
    response = client.get(f"/api/v1/orders/{uuid.uuid4()}")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "ORDER_NOT_FOUND"


# ---------------------------------------------------------------------------
# Exception handlers
# ---------------------------------------------------------------------------


def test_handle_order_error_returns_correct_status() -> None:
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/trigger")
    def trigger() -> None:
        raise CartHasNoItems("no items")

    test_client = TestClient(app)
    response = test_client.get("/trigger")

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "ORDER_CART_HAS_NO_ITEMS"
