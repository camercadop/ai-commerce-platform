import uuid

from fastapi.testclient import TestClient


CREATE_CART_PAYLOAD = {"session_id": "session-1"}
CLAIM_CART_PAYLOAD = {"customer_id": "00000000-0000-0000-0000-000000000001"}
ADD_ITEM_PAYLOAD = {
    "variant_id": "00000000-0000-0000-0000-000000000002",
    "quantity": 1,
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


def test_create_cart_returns_201(client: TestClient) -> None:
    response = client.post("/api/v1/cart", json=CREATE_CART_PAYLOAD)

    assert response.status_code == 201


def test_get_cart_returns_200(client: TestClient) -> None:
    created = client.post("/api/v1/cart", json=CREATE_CART_PAYLOAD).json()
    cart_id = created["id"]

    response = client.get(f"/api/v1/cart/{cart_id}")

    assert response.status_code == 200


def test_get_cart_not_found_returns_404(client: TestClient) -> None:
    response = client.get(f"/api/v1/cart/{uuid.uuid4()}")

    assert response.status_code == 404


def test_claim_cart_returns_200(client: TestClient) -> None:
    created = client.post("/api/v1/cart", json=CREATE_CART_PAYLOAD).json()
    cart_id = created["id"]

    response = client.post(f"/api/v1/cart/{cart_id}/claim", json=CLAIM_CART_PAYLOAD)

    assert response.status_code == 200


# ---------------------------------------------------------------------------
# Cart Items
# ---------------------------------------------------------------------------


def test_add_cart_item_returns_404(client: TestClient) -> None:
    cart = client.post("/api/v1/cart", json=CREATE_CART_PAYLOAD).json()
    cart_id = cart["id"]

    response = client.post(f"/api/v1/cart/{cart_id}/items", json=ADD_ITEM_PAYLOAD)

    assert response.status_code == 404


def test_update_cart_item_returns_404(client: TestClient) -> None:
    cart = client.post("/api/v1/cart", json=CREATE_CART_PAYLOAD).json()
    cart_id = cart["id"]

    response = client.patch(
        f"/api/v1/cart/{cart_id}/items/{uuid.uuid4()}",
        json={"quantity": 2},
    )

    assert response.status_code == 404


def test_remove_cart_item_returns_404(client: TestClient) -> None:
    cart = client.post("/api/v1/cart", json=CREATE_CART_PAYLOAD).json()
    cart_id = cart["id"]

    response = client.delete(f"/api/v1/cart/{cart_id}/items/{uuid.uuid4()}")

    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Cart Actions
# ---------------------------------------------------------------------------


def test_clear_cart_returns_204(client: TestClient) -> None:
    cart = client.post("/api/v1/cart", json=CREATE_CART_PAYLOAD).json()
    cart_id = cart["id"]

    response = client.delete(f"/api/v1/cart/{cart_id}/clear")

    assert response.status_code == 204
