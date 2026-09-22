import uuid

from faker import Faker
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.identity.routes import _auth_dependency
from app.identity.tests.conftest import ACTOR_SUB
from app.shared.auth import TokenClaims

fake = Faker()


def make_register_payload(**kwargs: object) -> dict[str, object]:
    """Build a valid register-customer request payload with randomised defaults."""
    return {
        "identity_provider_id": ACTOR_SUB,
        "email": fake.email(),
        "first_name": fake.first_name(),
        "last_name": fake.last_name(),
        **kwargs,
    }


def make_address_payload(**kwargs: object) -> dict[str, object]:
    """Build a valid add-address request payload with randomised defaults."""
    return {
        "label": fake.word(),
        "street": fake.street_address(),
        "city": fake.city(),
        "state": fake.state_abbr(),
        "country": fake.country_code(),
        "postal_code": fake.postcode(),
        "is_default": False,
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
# Customers
# ---------------------------------------------------------------------------


def test_smoke_register_customer(client: TestClient) -> None:
    response = client.post("/api/v1/customers", json=make_register_payload())

    assert response.status_code == 201


def test_register_customer_returns_expected_body(client: TestClient) -> None:
    payload = make_register_payload()
    data = client.post("/api/v1/customers", json=payload).json()

    assert data["email"] == payload["email"]
    assert data["first_name"] == payload["first_name"]
    assert data["last_name"] == payload["last_name"]


def test_register_customer_conflict_returns_409(client: TestClient) -> None:
    payload = make_register_payload()
    client.post("/api/v1/customers", json=payload)
    response = client.post("/api/v1/customers", json=payload)

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "CUSTOMER_ALREADY_EXISTS"


def test_smoke_get_customer(client: TestClient) -> None:
    created = client.post("/api/v1/customers", json=make_register_payload()).json()

    response = client.get(f"/api/v1/customers/{created['id']}")

    assert response.status_code == 200


def test_get_customer_returns_expected_body(client: TestClient) -> None:
    payload = make_register_payload()
    created_id = client.post("/api/v1/customers", json=payload).json()["id"]

    data = client.get(f"/api/v1/customers/{created_id}").json()

    assert data["id"] == created_id
    assert data["email"] == payload["email"]


def test_get_customer_not_found_returns_404(client: TestClient) -> None:
    response = client.get(f"/api/v1/customers/{uuid.uuid4()}")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "CUSTOMER_NOT_FOUND"


def test_smoke_update_customer(client: TestClient) -> None:
    created = client.post("/api/v1/customers", json=make_register_payload()).json()

    response = client.patch(
        f"/api/v1/customers/{created['id']}", json={"first_name": fake.first_name()}
    )

    assert response.status_code == 200


def test_update_customer_returns_expected_body(client: TestClient) -> None:
    created_id = client.post("/api/v1/customers", json=make_register_payload()).json()["id"]

    data = client.patch(
        f"/api/v1/customers/{created_id}", json={"first_name": "Alice"}
    ).json()

    assert data["id"] == created_id
    assert data["first_name"] == "Alice"


def test_smoke_upsert_preferences(client: TestClient) -> None:
    created = client.post("/api/v1/customers", json=make_register_payload()).json()

    response = client.patch(
        f"/api/v1/customers/{created['id']}/preferences",
        json={"preferences": {"language": "en"}},
    )

    assert response.status_code == 200


# ---------------------------------------------------------------------------
# Addresses
# ---------------------------------------------------------------------------


def test_smoke_add_address(client: TestClient) -> None:
    created = client.post("/api/v1/customers", json=make_register_payload()).json()

    response = client.post(
        f"/api/v1/customers/{created['id']}/addresses", json=make_address_payload()
    )

    assert response.status_code == 201


def test_add_address_returns_expected_body(client: TestClient) -> None:
    customer_id = client.post("/api/v1/customers", json=make_register_payload()).json()["id"]
    payload = make_address_payload()

    data = client.post(
        f"/api/v1/customers/{customer_id}/addresses", json=payload
    ).json()

    assert data["customer_id"] == customer_id
    assert data["label"] == payload["label"]
    assert data["city"] == payload["city"]


def test_smoke_list_addresses(client: TestClient) -> None:
    created = client.post("/api/v1/customers", json=make_register_payload()).json()

    response = client.get(f"/api/v1/customers/{created['id']}/addresses")

    assert response.status_code == 200


def test_smoke_update_address(client: TestClient) -> None:
    customer_id = client.post("/api/v1/customers", json=make_register_payload()).json()["id"]
    address = client.post(
        f"/api/v1/customers/{customer_id}/addresses", json=make_address_payload()
    ).json()

    response = client.patch(
        f"/api/v1/customers/{customer_id}/addresses/{address['id']}",
        json={"city": fake.city()},
    )

    assert response.status_code == 200


def test_update_address_returns_expected_body(client: TestClient) -> None:
    customer_id = client.post("/api/v1/customers", json=make_register_payload()).json()["id"]
    address_id = client.post(
        f"/api/v1/customers/{customer_id}/addresses", json=make_address_payload()
    ).json()["id"]

    data = client.patch(
        f"/api/v1/customers/{customer_id}/addresses/{address_id}",
        json={"city": "Shelbyville"},
    ).json()

    assert data["id"] == address_id
    assert data["city"] == "Shelbyville"


def test_smoke_remove_address(client: TestClient) -> None:
    customer_id = client.post("/api/v1/customers", json=make_register_payload()).json()["id"]
    address = client.post(
        f"/api/v1/customers/{customer_id}/addresses", json=make_address_payload()
    ).json()

    response = client.delete(
        f"/api/v1/customers/{customer_id}/addresses/{address['id']}"
    )

    assert response.status_code == 204


# ---------------------------------------------------------------------------
# Ownership guard
# ---------------------------------------------------------------------------


def test_require_owner_returns_404_when_customer_not_found(client: TestClient) -> None:
    response = client.get(f"/api/v1/customers/{uuid.uuid4()}/addresses")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "CUSTOMER_NOT_FOUND"


def test_require_owner_returns_404_when_customer_not_owned(
    app: FastAPI, client: TestClient
) -> None:
    created = client.post("/api/v1/customers", json=make_register_payload()).json()
    customer_id = created["id"]

    different_claims = TokenClaims(sub="different-sub", email="other@example.com")
    app.dependency_overrides[_auth_dependency] = lambda: different_claims

    response = client.get(f"/api/v1/customers/{customer_id}/addresses")

    assert response.status_code == 404
