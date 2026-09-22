import uuid

from faker import Faker
from fastapi.testclient import TestClient

fake = Faker()


def make_category_payload(**kwargs: object) -> dict[str, object]:
    """Build a valid create-category request payload with randomised defaults."""
    return {
        "name": fake.word(),
        "description": None,
        "parent_id": None,
        **kwargs,
    }


def make_brand_payload(**kwargs: object) -> dict[str, object]:
    """Build a valid create-brand request payload with randomised defaults."""
    return {
        "name": fake.company(),
        "website": None,
        "contact_email": None,
        "description": None,
        **kwargs,
    }


def make_product_payload(**kwargs: object) -> dict[str, object]:
    """Build a valid create-product request payload with randomised defaults."""
    return {
        "sku": fake.bothify("SKU-###"),
        "name": fake.word(),
        "base_price": "9.99",
        **kwargs,
    }


def make_variant_payload(**kwargs: object) -> dict[str, object]:
    """Build a valid create-variant request payload with randomised defaults."""
    return {
        "sku": fake.bothify("VAR-###"),
        "price": "4.99",
        "attributes": {},
        **kwargs,
    }


def make_attribute_payload(**kwargs: object) -> dict[str, object]:
    """Build a valid create-attribute request payload with randomised defaults."""
    return {
        "key": fake.word(),
        "value_type": "string",
        "required": False,
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
# Categories
# ---------------------------------------------------------------------------


def test_smoke_create_category(client: TestClient) -> None:
    response = client.post("/api/v1/catalog/categories", json=make_category_payload())

    assert response.status_code == 201


def test_create_category_returns_expected_body(client: TestClient) -> None:
    payload = make_category_payload()
    data = client.post("/api/v1/catalog/categories", json=payload).json()

    assert data["name"] == payload["name"]
    assert data["parent_id"] is None


def test_create_category_conflict_returns_409(client: TestClient) -> None:
    payload = make_category_payload()
    client.post("/api/v1/catalog/categories", json=payload)
    response = client.post("/api/v1/catalog/categories", json=payload)

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "CATEGORY_ALREADY_EXISTS"


def test_smoke_get_category(client: TestClient) -> None:
    created = client.post("/api/v1/catalog/categories", json=make_category_payload()).json()

    response = client.get(f"/api/v1/catalog/categories/{created['id']}")

    assert response.status_code == 200


def test_get_category_returns_expected_body(client: TestClient) -> None:
    payload = make_category_payload()
    created_id = client.post("/api/v1/catalog/categories", json=payload).json()["id"]

    data = client.get(f"/api/v1/catalog/categories/{created_id}").json()

    assert data["id"] == created_id
    assert data["name"] == payload["name"]


def test_get_category_not_found_returns_404(client: TestClient) -> None:
    response = client.get(f"/api/v1/catalog/categories/{uuid.uuid4()}")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "CATEGORY_NOT_FOUND"


def test_smoke_update_category(client: TestClient) -> None:
    created = client.post("/api/v1/catalog/categories", json=make_category_payload()).json()

    response = client.patch(
        f"/api/v1/catalog/categories/{created['id']}", json={"name": fake.word()}
    )

    assert response.status_code == 200


def test_update_category_returns_expected_body(client: TestClient) -> None:
    created_id = client.post(
        "/api/v1/catalog/categories", json=make_category_payload()
    ).json()["id"]

    data = client.patch(
        f"/api/v1/catalog/categories/{created_id}", json={"name": "Updated"}
    ).json()

    assert data["id"] == created_id
    assert data["name"] == "Updated"


def test_smoke_delete_category(client: TestClient) -> None:
    created = client.post("/api/v1/catalog/categories", json=make_category_payload()).json()

    response = client.delete(f"/api/v1/catalog/categories/{created['id']}")

    assert response.status_code == 204


def test_smoke_list_root_categories(client: TestClient) -> None:
    response = client.get("/api/v1/catalog/categories")

    assert response.status_code == 200


def test_smoke_list_category_children(client: TestClient) -> None:
    parent = client.post("/api/v1/catalog/categories", json=make_category_payload()).json()

    response = client.get(f"/api/v1/catalog/categories/{parent['id']}/children")

    assert response.status_code == 200


# ---------------------------------------------------------------------------
# Brands
# ---------------------------------------------------------------------------


def test_smoke_create_brand(client: TestClient) -> None:
    response = client.post("/api/v1/catalog/brands", json=make_brand_payload())

    assert response.status_code == 201


def test_create_brand_returns_expected_body(client: TestClient) -> None:
    payload = make_brand_payload()
    data = client.post("/api/v1/catalog/brands", json=payload).json()

    assert data["name"] == payload["name"]


def test_create_brand_conflict_returns_409(client: TestClient) -> None:
    payload = make_brand_payload()
    client.post("/api/v1/catalog/brands", json=payload)
    response = client.post("/api/v1/catalog/brands", json=payload)

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "BRAND_ALREADY_EXISTS"


def test_smoke_get_brand(client: TestClient) -> None:
    created = client.post("/api/v1/catalog/brands", json=make_brand_payload()).json()

    response = client.get(f"/api/v1/catalog/brands/{created['id']}")

    assert response.status_code == 200


def test_get_brand_returns_expected_body(client: TestClient) -> None:
    payload = make_brand_payload()
    created_id = client.post("/api/v1/catalog/brands", json=payload).json()["id"]

    data = client.get(f"/api/v1/catalog/brands/{created_id}").json()

    assert data["id"] == created_id
    assert data["name"] == payload["name"]


def test_get_brand_not_found_returns_404(client: TestClient) -> None:
    response = client.get(f"/api/v1/catalog/brands/{uuid.uuid4()}")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "BRAND_NOT_FOUND"


def test_smoke_update_brand(client: TestClient) -> None:
    created = client.post("/api/v1/catalog/brands", json=make_brand_payload()).json()

    response = client.patch(
        f"/api/v1/catalog/brands/{created['id']}", json={"name": fake.company()}
    )

    assert response.status_code == 200


def test_update_brand_returns_expected_body(client: TestClient) -> None:
    created_id = client.post("/api/v1/catalog/brands", json=make_brand_payload()).json()["id"]

    data = client.patch(
        f"/api/v1/catalog/brands/{created_id}", json={"name": "Updated"}
    ).json()

    assert data["id"] == created_id
    assert data["name"] == "Updated"


def test_smoke_delete_brand(client: TestClient) -> None:
    created = client.post("/api/v1/catalog/brands", json=make_brand_payload()).json()

    response = client.delete(f"/api/v1/catalog/brands/{created['id']}")

    assert response.status_code == 204


# ---------------------------------------------------------------------------
# Products
# ---------------------------------------------------------------------------


def test_smoke_create_product(client: TestClient) -> None:
    response = client.post("/api/v1/catalog/products", json=make_product_payload())

    assert response.status_code == 201


def test_create_product_returns_expected_body(client: TestClient) -> None:
    payload = make_product_payload()
    data = client.post("/api/v1/catalog/products", json=payload).json()

    assert data["sku"] == payload["sku"]
    assert data["name"] == payload["name"]
    assert data["base_price"] == payload["base_price"]


def test_create_product_conflict_returns_409(client: TestClient) -> None:
    payload = make_product_payload()
    client.post("/api/v1/catalog/products", json=payload)
    response = client.post("/api/v1/catalog/products", json=payload)

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "PRODUCT_ALREADY_EXISTS"


def test_smoke_get_product(client: TestClient) -> None:
    created = client.post("/api/v1/catalog/products", json=make_product_payload()).json()

    response = client.get(f"/api/v1/catalog/products/{created['id']}")

    assert response.status_code == 200


def test_get_product_returns_expected_body(client: TestClient) -> None:
    payload = make_product_payload()
    created_id = client.post("/api/v1/catalog/products", json=payload).json()["id"]

    data = client.get(f"/api/v1/catalog/products/{created_id}").json()

    assert data["id"] == created_id
    assert data["sku"] == payload["sku"]


def test_get_product_not_found_returns_404(client: TestClient) -> None:
    response = client.get(f"/api/v1/catalog/products/{uuid.uuid4()}")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "PRODUCT_NOT_FOUND"


def test_smoke_update_product(client: TestClient) -> None:
    created = client.post("/api/v1/catalog/products", json=make_product_payload()).json()

    response = client.patch(
        f"/api/v1/catalog/products/{created['id']}", json={"name": fake.word()}
    )

    assert response.status_code == 200


def test_update_product_returns_expected_body(client: TestClient) -> None:
    created_id = client.post(
        "/api/v1/catalog/products", json=make_product_payload()
    ).json()["id"]

    data = client.patch(
        f"/api/v1/catalog/products/{created_id}", json={"name": "Updated"}
    ).json()

    assert data["id"] == created_id
    assert data["name"] == "Updated"


def test_smoke_delete_product(client: TestClient) -> None:
    created = client.post("/api/v1/catalog/products", json=make_product_payload()).json()

    response = client.delete(f"/api/v1/catalog/products/{created['id']}")

    assert response.status_code == 204


def test_smoke_list_brand_products(client: TestClient) -> None:
    brand = client.post("/api/v1/catalog/brands", json=make_brand_payload()).json()

    response = client.get(f"/api/v1/catalog/brands/{brand['id']}/products")

    assert response.status_code == 200


def test_smoke_list_category_products(client: TestClient) -> None:
    category = client.post("/api/v1/catalog/categories", json=make_category_payload()).json()

    response = client.get(f"/api/v1/catalog/categories/{category['id']}/products")

    assert response.status_code == 200


# ---------------------------------------------------------------------------
# Variants
# ---------------------------------------------------------------------------


def test_smoke_create_variant(client: TestClient) -> None:
    product = client.post("/api/v1/catalog/products", json=make_product_payload()).json()

    response = client.post(
        f"/api/v1/catalog/products/{product['id']}/variants", json=make_variant_payload()
    )

    assert response.status_code == 201


def test_create_variant_returns_expected_body(client: TestClient) -> None:
    product_id = client.post(
        "/api/v1/catalog/products", json=make_product_payload()
    ).json()["id"]
    payload = make_variant_payload()

    data = client.post(
        f"/api/v1/catalog/products/{product_id}/variants", json=payload
    ).json()

    assert data["sku"] == payload["sku"]
    assert data["price"] == payload["price"]
    assert data["product_id"] == product_id


def test_create_variant_conflict_returns_409(client: TestClient) -> None:
    product = client.post("/api/v1/catalog/products", json=make_product_payload()).json()
    payload = make_variant_payload()
    client.post(f"/api/v1/catalog/products/{product['id']}/variants", json=payload)

    response = client.post(
        f"/api/v1/catalog/products/{product['id']}/variants", json=payload
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "VARIANT_ALREADY_EXISTS"


def test_smoke_get_variant(client: TestClient) -> None:
    product = client.post("/api/v1/catalog/products", json=make_product_payload()).json()
    variant = client.post(
        f"/api/v1/catalog/products/{product['id']}/variants", json=make_variant_payload()
    ).json()

    response = client.get(
        f"/api/v1/catalog/products/{product['id']}/variants/{variant['id']}"
    )

    assert response.status_code == 200


def test_get_variant_returns_expected_body(client: TestClient) -> None:
    product_id = client.post(
        "/api/v1/catalog/products", json=make_product_payload()
    ).json()["id"]
    payload = make_variant_payload()
    variant_id = client.post(
        f"/api/v1/catalog/products/{product_id}/variants", json=payload
    ).json()["id"]

    data = client.get(
        f"/api/v1/catalog/products/{product_id}/variants/{variant_id}"
    ).json()

    assert data["id"] == variant_id
    assert data["sku"] == payload["sku"]


def test_get_variant_not_found_returns_404(client: TestClient) -> None:
    product = client.post("/api/v1/catalog/products", json=make_product_payload()).json()

    response = client.get(
        f"/api/v1/catalog/products/{product['id']}/variants/{uuid.uuid4()}"
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "VARIANT_NOT_FOUND"


def test_smoke_list_product_variants(client: TestClient) -> None:
    product = client.post("/api/v1/catalog/products", json=make_product_payload()).json()

    response = client.get(f"/api/v1/catalog/products/{product['id']}/variants")

    assert response.status_code == 200


def test_smoke_delete_variant(client: TestClient) -> None:
    product = client.post("/api/v1/catalog/products", json=make_product_payload()).json()
    variant = client.post(
        f"/api/v1/catalog/products/{product['id']}/variants", json=make_variant_payload()
    ).json()

    response = client.delete(
        f"/api/v1/catalog/products/{product['id']}/variants/{variant['id']}"
    )

    assert response.status_code == 204


# ---------------------------------------------------------------------------
# Category Attributes
# ---------------------------------------------------------------------------


def test_smoke_create_attribute(client: TestClient) -> None:
    category = client.post("/api/v1/catalog/categories", json=make_category_payload()).json()

    response = client.post(
        f"/api/v1/catalog/categories/{category['id']}/attributes",
        json=make_attribute_payload(),
    )

    assert response.status_code == 201


def test_create_attribute_returns_expected_body(client: TestClient) -> None:
    category_id = client.post(
        "/api/v1/catalog/categories", json=make_category_payload()
    ).json()["id"]
    payload = make_attribute_payload()

    data = client.post(
        f"/api/v1/catalog/categories/{category_id}/attributes", json=payload
    ).json()

    assert data["key"] == payload["key"]
    assert data["value_type"] == payload["value_type"]
    assert data["category_id"] == category_id


def test_create_attribute_conflict_returns_409(client: TestClient) -> None:
    category = client.post("/api/v1/catalog/categories", json=make_category_payload()).json()
    payload = make_attribute_payload()
    client.post(
        f"/api/v1/catalog/categories/{category['id']}/attributes", json=payload
    )

    response = client.post(
        f"/api/v1/catalog/categories/{category['id']}/attributes", json=payload
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "CATEGORY_ATTRIBUTE_ALREADY_EXISTS"


def test_smoke_get_attribute(client: TestClient) -> None:
    category = client.post("/api/v1/catalog/categories", json=make_category_payload()).json()
    attr = client.post(
        f"/api/v1/catalog/categories/{category['id']}/attributes",
        json=make_attribute_payload(),
    ).json()

    response = client.get(
        f"/api/v1/catalog/categories/{category['id']}/attributes/{attr['id']}"
    )

    assert response.status_code == 200


def test_get_attribute_returns_expected_body(client: TestClient) -> None:
    category_id = client.post(
        "/api/v1/catalog/categories", json=make_category_payload()
    ).json()["id"]
    payload = make_attribute_payload()
    attr_id = client.post(
        f"/api/v1/catalog/categories/{category_id}/attributes", json=payload
    ).json()["id"]

    data = client.get(
        f"/api/v1/catalog/categories/{category_id}/attributes/{attr_id}"
    ).json()

    assert data["id"] == attr_id
    assert data["key"] == payload["key"]


def test_get_attribute_not_found_returns_404(client: TestClient) -> None:
    category = client.post("/api/v1/catalog/categories", json=make_category_payload()).json()

    response = client.get(
        f"/api/v1/catalog/categories/{category['id']}/attributes/{uuid.uuid4()}"
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "CATEGORY_ATTRIBUTE_NOT_FOUND"


def test_smoke_list_category_attributes(client: TestClient) -> None:
    category = client.post("/api/v1/catalog/categories", json=make_category_payload()).json()

    response = client.get(f"/api/v1/catalog/categories/{category['id']}/attributes")

    assert response.status_code == 200


def test_smoke_delete_attribute(client: TestClient) -> None:
    category = client.post("/api/v1/catalog/categories", json=make_category_payload()).json()
    attr = client.post(
        f"/api/v1/catalog/categories/{category['id']}/attributes",
        json=make_attribute_payload(),
    ).json()

    response = client.delete(
        f"/api/v1/catalog/categories/{category['id']}/attributes/{attr['id']}"
    )

    assert response.status_code == 204
