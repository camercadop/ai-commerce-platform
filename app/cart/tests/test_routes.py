import os
import uuid
from decimal import Decimal
from unittest.mock import patch

from faker import Faker
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import update

from app.cart.adapters import StubCatalogPort, StubInventoryPort
from app.cart.exceptions import SessionCartConflict
from app.cart.models import Cart, CartItem
from app.cart.routes import register_exception_handlers
from app.shared.db import build_session_factory

fake = Faker()


def make_create_cart_payload(**kwargs: object) -> dict[str, object]:
    """Build a valid create-cart request payload with randomised defaults."""
    return {
        "session_id": str(uuid.uuid4()),
        **kwargs,
    }


def make_claim_cart_payload(**kwargs: object) -> dict[str, object]:
    """Build a valid claim-cart request payload with randomised defaults."""
    return {
        "customer_id": str(uuid.uuid4()),
        **kwargs,
    }


def make_add_item_payload(**kwargs: object) -> dict[str, object]:
    """Build a valid add-cart-item request payload with randomised defaults."""
    return {
        "variant_id": str(uuid.uuid4()),
        "quantity": 1,
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
# Carts
# ---------------------------------------------------------------------------


def test_smoke_create_cart(client: TestClient) -> None:
    response = client.post("/api/v1/cart", json=make_create_cart_payload())

    assert response.status_code == 201


def test_create_cart_returns_expected_body(client: TestClient) -> None:
    payload = make_create_cart_payload()
    data = client.post("/api/v1/cart", json=payload).json()

    assert data["session_id"] == payload["session_id"]
    assert data["status"] == "active"
    assert data["items"] == []
    assert data["subtotal"] == "0"


def test_smoke_get_cart(client: TestClient) -> None:
    created = client.post("/api/v1/cart", json=make_create_cart_payload()).json()
    cart_id = created["id"]

    response = client.get(f"/api/v1/cart/{cart_id}")

    assert response.status_code == 200


def test_get_cart_returns_expected_body(client: TestClient) -> None:
    payload = make_create_cart_payload()
    cart_id = client.post("/api/v1/cart", json=payload).json()["id"]

    data = client.get(f"/api/v1/cart/{cart_id}").json()

    assert data["id"] == cart_id
    assert data["session_id"] == payload["session_id"]


def test_get_cart_not_found_returns_404(client: TestClient) -> None:
    response = client.get(f"/api/v1/cart/{uuid.uuid4()}")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "CART_NOT_FOUND"


def test_smoke_claim_cart(client: TestClient) -> None:
    created = client.post("/api/v1/cart", json=make_create_cart_payload()).json()
    cart_id = created["id"]

    response = client.post(f"/api/v1/cart/{cart_id}/claim", json=make_claim_cart_payload())

    assert response.status_code == 200


def test_claim_cart_returns_expected_body(client: TestClient) -> None:
    cart_id = client.post("/api/v1/cart", json=make_create_cart_payload()).json()["id"]
    payload = make_claim_cart_payload()

    data = client.post(f"/api/v1/cart/{cart_id}/claim", json=payload).json()

    assert data["id"] == cart_id
    assert data["customer_id"] == payload["customer_id"]


# ---------------------------------------------------------------------------
# Cart Items
# ---------------------------------------------------------------------------


def test_add_cart_item_returns_404(client: TestClient) -> None:
    cart_id = client.post("/api/v1/cart", json=make_create_cart_payload()).json()["id"]

    response = client.post(f"/api/v1/cart/{cart_id}/items", json=make_add_item_payload())

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "CART_VARIANT_NOT_FOUND"


def test_update_cart_item_returns_404(client: TestClient) -> None:
    cart_id = client.post("/api/v1/cart", json=make_create_cart_payload()).json()["id"]

    response = client.patch(
        f"/api/v1/cart/{cart_id}/items/{uuid.uuid4()}",
        json={"quantity": 2},
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "CART_ITEM_NOT_FOUND"


def test_remove_cart_item_returns_404(client: TestClient) -> None:
    cart_id = client.post("/api/v1/cart", json=make_create_cart_payload()).json()["id"]

    response = client.delete(f"/api/v1/cart/{cart_id}/items/{uuid.uuid4()}")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "CART_ITEM_NOT_FOUND"


# ---------------------------------------------------------------------------
# Cart Actions
# ---------------------------------------------------------------------------


def test_smoke_clear_cart(client: TestClient) -> None:
    cart_id = client.post("/api/v1/cart", json=make_create_cart_payload()).json()["id"]

    response = client.delete(f"/api/v1/cart/{cart_id}/clear")

    assert response.status_code == 204


# ---------------------------------------------------------------------------
# add_cart_item
# ---------------------------------------------------------------------------


def test_smoke_add_cart_item(client: TestClient) -> None:
    with patch.object(
        StubCatalogPort, "get_variant_price", return_value=Decimal("9.99")
    ):
        cart_id = client.post("/api/v1/cart", json=make_create_cart_payload()).json()["id"]

        response = client.post(f"/api/v1/cart/{cart_id}/items", json=make_add_item_payload())

        assert response.status_code == 201


def test_add_cart_item_returns_expected_body(client: TestClient) -> None:
    with patch.object(
        StubCatalogPort, "get_variant_price", return_value=Decimal("9.99")
    ):
        cart_id = client.post("/api/v1/cart", json=make_create_cart_payload()).json()["id"]
        payload = make_add_item_payload()

        data = client.post(f"/api/v1/cart/{cart_id}/items", json=payload).json()

        assert data["variant_id"] == payload["variant_id"]
        assert data["quantity"] == payload["quantity"]
        assert data["unit_price"] == "9.99"


def test_add_cart_item_returns_400_when_cart_not_active(client: TestClient) -> None:
    cart_id = client.post("/api/v1/cart", json=make_create_cart_payload()).json()["id"]

    session_factory = build_session_factory(os.environ["TEST_DATABASE_URL"])
    with session_factory() as session:
        session.execute(
            update(Cart).where(Cart.id == cart_id).values(status="checked_out")
        )
        session.commit()

    response = client.post(f"/api/v1/cart/{cart_id}/items", json=make_add_item_payload())

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "CART_INVALID_STATUS"


def test_add_cart_item_returns_409_when_inventory_unavailable(
    client: TestClient,
) -> None:
    with (
        patch.object(
            StubCatalogPort, "get_variant_price", return_value=Decimal("9.99")
        ),
        patch.object(StubInventoryPort, "check_availability", return_value=False),
    ):
        cart_id = client.post("/api/v1/cart", json=make_create_cart_payload()).json()["id"]

        response = client.post(f"/api/v1/cart/{cart_id}/items", json=make_add_item_payload())

        assert response.status_code == 409
        assert response.json()["error"]["code"] == "CART_INVENTORY_UNAVAILABLE"


# ---------------------------------------------------------------------------
# update_cart_item
# ---------------------------------------------------------------------------


def test_smoke_update_cart_item(client: TestClient) -> None:
    with patch.object(
        StubCatalogPort, "get_variant_price", return_value=Decimal("9.99")
    ):
        cart_id = client.post("/api/v1/cart", json=make_create_cart_payload()).json()["id"]
        client.post(f"/api/v1/cart/{cart_id}/items", json=make_add_item_payload())
        item_id = client.get(f"/api/v1/cart/{cart_id}").json()["items"][0]["id"]

        response = client.patch(
            f"/api/v1/cart/{cart_id}/items/{item_id}",
            json={"quantity": 5},
        )

        assert response.status_code == 200


def test_update_cart_item_returns_expected_body(client: TestClient) -> None:
    with patch.object(
        StubCatalogPort, "get_variant_price", return_value=Decimal("9.99")
    ):
        cart_id = client.post("/api/v1/cart", json=make_create_cart_payload()).json()["id"]
        client.post(f"/api/v1/cart/{cart_id}/items", json=make_add_item_payload())
        item_id = client.get(f"/api/v1/cart/{cart_id}").json()["items"][0]["id"]

        data = client.patch(
            f"/api/v1/cart/{cart_id}/items/{item_id}",
            json={"quantity": 5},
        ).json()

        assert data["id"] == item_id
        assert data["quantity"] == 5


def test_update_cart_item_returns_400_when_cart_not_active(client: TestClient) -> None:
    cart_id = client.post("/api/v1/cart", json=make_create_cart_payload()).json()["id"]

    session_factory = build_session_factory(os.environ["TEST_DATABASE_URL"])
    with session_factory() as session:
        session.execute(
            update(Cart).where(Cart.id == cart_id).values(status="checked_out")
        )
        session.commit()

    response = client.patch(
        f"/api/v1/cart/{cart_id}/items/{uuid.uuid4()}",
        json={"quantity": 2},
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "CART_INVALID_STATUS"


def test_update_cart_item_returns_409_when_inventory_unavailable(
    client: TestClient,
) -> None:
    with patch.object(
        StubCatalogPort, "get_variant_price", return_value=Decimal("9.99")
    ):
        cart_id = client.post("/api/v1/cart", json=make_create_cart_payload()).json()["id"]
        client.post(f"/api/v1/cart/{cart_id}/items", json=make_add_item_payload())
        item_id = client.get(f"/api/v1/cart/{cart_id}").json()["items"][0]["id"]

    with (
        patch.object(
            StubCatalogPort, "get_variant_price", return_value=Decimal("9.99")
        ),
        patch.object(StubInventoryPort, "check_availability", return_value=False),
    ):
        response = client.patch(
            f"/api/v1/cart/{cart_id}/items/{item_id}",
            json={"quantity": 5},
        )

        assert response.status_code == 409
        assert response.json()["error"]["code"] == "CART_INVENTORY_UNAVAILABLE"


# ---------------------------------------------------------------------------
# remove_cart_item
# ---------------------------------------------------------------------------


def test_smoke_remove_cart_item(client: TestClient) -> None:
    with patch.object(
        StubCatalogPort, "get_variant_price", return_value=Decimal("9.99")
    ):
        cart_id = client.post("/api/v1/cart", json=make_create_cart_payload()).json()["id"]
        client.post(f"/api/v1/cart/{cart_id}/items", json=make_add_item_payload())
        item_id = client.get(f"/api/v1/cart/{cart_id}").json()["items"][0]["id"]

        response = client.delete(f"/api/v1/cart/{cart_id}/items/{item_id}")

        assert response.status_code == 204


def test_remove_cart_item_returns_400_when_cart_not_active(client: TestClient) -> None:
    cart_id = client.post("/api/v1/cart", json=make_create_cart_payload()).json()["id"]

    session_factory = build_session_factory(os.environ["TEST_DATABASE_URL"])
    with session_factory() as session:
        session.execute(
            update(Cart).where(Cart.id == cart_id).values(status="checked_out")
        )
        session.commit()

    response = client.delete(f"/api/v1/cart/{cart_id}/items/{uuid.uuid4()}")

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "CART_INVALID_STATUS"


# ---------------------------------------------------------------------------
# Exception handlers
# ---------------------------------------------------------------------------


def test_handle_merge_conflict_returns_409(client: TestClient) -> None:
    customer_id = str(uuid.uuid4())
    client.post(
        "/api/v1/cart",
        json=make_create_cart_payload(customer_id=customer_id),
    )

    anon_cart_id = client.post("/api/v1/cart", json=make_create_cart_payload()).json()["id"]

    session_factory = build_session_factory(os.environ["TEST_DATABASE_URL"])
    with session_factory() as session:
        item = CartItem(
            cart_id=anon_cart_id,
            variant_id=uuid.uuid4(),
            quantity=1,
            unit_price=Decimal("9.99"),
        )
        session.add(item)
        session.commit()

    response = client.post(
        f"/api/v1/cart/{anon_cart_id}/claim",
        json={"customer_id": customer_id},
    )
    assert response.status_code == 409


def test_handle_session_cart_conflict_returns_409() -> None:
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/trigger")
    def trigger() -> None:
        raise SessionCartConflict("session conflict")

    client = TestClient(app)
    response = client.get("/trigger")
    assert response.status_code == 409
