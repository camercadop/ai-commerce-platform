import uuid

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.identity.routes import _auth_dependency
from app.shared.auth import TokenClaims

REGISTER_PAYLOAD = {
    "identity_provider_id": "sub-test",
    "email": "jane@example.com",
    "first_name": "Jane",
    "last_name": "Doe",
}

ADDRESS_PAYLOAD = {
    "label": "Home",
    "street": "123 Main St",
    "city": "Springfield",
    "state": "IL",
    "country": "US",
    "postal_code": "62701",
    "is_default": False,
}


def test_register_customer_returns_201(client: TestClient) -> None:
    response = client.post("/api/v1/customers", json=REGISTER_PAYLOAD)

    assert response.status_code == 201


def test_register_customer_conflict_returns_409(client: TestClient) -> None:
    client.post("/api/v1/customers", json=REGISTER_PAYLOAD)
    response = client.post("/api/v1/customers", json=REGISTER_PAYLOAD)

    assert response.status_code == 409


def test_get_customer_returns_200(client: TestClient) -> None:
    created = client.post("/api/v1/customers", json=REGISTER_PAYLOAD).json()
    customer_id = created["id"]

    response = client.get(f"/api/v1/customers/{customer_id}")

    assert response.status_code == 200


def test_get_customer_not_found_returns_404(client: TestClient) -> None:
    response = client.get(f"/api/v1/customers/{uuid.uuid4()}")

    assert response.status_code == 404


def test_update_customer_returns_200(client: TestClient) -> None:
    created = client.post("/api/v1/customers", json=REGISTER_PAYLOAD).json()
    customer_id = created["id"]

    response = client.patch(
        f"/api/v1/customers/{customer_id}", json={"first_name": "Alice"}
    )

    assert response.status_code == 200


def test_upsert_preferences_returns_200(client: TestClient) -> None:
    created = client.post("/api/v1/customers", json=REGISTER_PAYLOAD).json()
    customer_id = created["id"]

    response = client.patch(
        f"/api/v1/customers/{customer_id}/preferences",
        json={"preferences": {"language": "en"}},
    )

    assert response.status_code == 200


def test_add_address_returns_201(client: TestClient) -> None:
    created = client.post("/api/v1/customers", json=REGISTER_PAYLOAD).json()
    customer_id = created["id"]

    response = client.post(
        f"/api/v1/customers/{customer_id}/addresses", json=ADDRESS_PAYLOAD
    )

    assert response.status_code == 201


def test_list_addresses_returns_200(client: TestClient) -> None:
    created = client.post("/api/v1/customers", json=REGISTER_PAYLOAD).json()
    customer_id = created["id"]

    response = client.get(f"/api/v1/customers/{customer_id}/addresses")

    assert response.status_code == 200


def test_update_address_returns_200(client: TestClient) -> None:
    created = client.post("/api/v1/customers", json=REGISTER_PAYLOAD).json()
    customer_id = created["id"]
    address = client.post(
        f"/api/v1/customers/{customer_id}/addresses", json=ADDRESS_PAYLOAD
    ).json()

    response = client.patch(
        f"/api/v1/customers/{customer_id}/addresses/{address['id']}",
        json={"city": "Shelbyville"},
    )

    assert response.status_code == 200


def test_remove_address_returns_204(client: TestClient) -> None:
    created = client.post("/api/v1/customers", json=REGISTER_PAYLOAD).json()
    customer_id = created["id"]
    address = client.post(
        f"/api/v1/customers/{customer_id}/addresses", json=ADDRESS_PAYLOAD
    ).json()

    response = client.delete(
        f"/api/v1/customers/{customer_id}/addresses/{address['id']}"
    )

    assert response.status_code == 204


def test_health_returns_ok(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_require_owner_returns_404_when_customer_not_found(client: TestClient) -> None:
    response = client.get(f"/api/v1/customers/{uuid.uuid4()}/addresses")

    assert response.status_code == 404


def test_require_owner_returns_404_when_customer_not_owned(
    app: FastAPI, client: TestClient
) -> None:
    created = client.post("/api/v1/customers", json=REGISTER_PAYLOAD).json()
    customer_id = created["id"]

    different_claims = TokenClaims(sub="different-sub", email="other@example.com")
    app.dependency_overrides[_auth_dependency] = lambda: different_claims

    response = client.get(f"/api/v1/customers/{customer_id}/addresses")

    assert response.status_code == 404
