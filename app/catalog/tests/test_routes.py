import uuid

from fastapi.testclient import TestClient

CATEGORY_PAYLOAD = {"name": "Electronics", "description": None, "parent_id": None}
BRAND_PAYLOAD = {
    "name": "Acme",
    "website": None,
    "contact_email": None,
    "description": None,
}
PRODUCT_PAYLOAD = {"sku": "SKU-001", "name": "Widget", "base_price": "9.99"}


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


def test_create_category_returns_201(client: TestClient) -> None:
    response = client.post("/api/v1/catalog/categories", json=CATEGORY_PAYLOAD)

    assert response.status_code == 201


def test_create_category_conflict_returns_409(client: TestClient) -> None:
    client.post("/api/v1/catalog/categories", json=CATEGORY_PAYLOAD)
    response = client.post("/api/v1/catalog/categories", json=CATEGORY_PAYLOAD)

    assert response.status_code == 409


def test_get_category_returns_200(client: TestClient) -> None:
    created = client.post("/api/v1/catalog/categories", json=CATEGORY_PAYLOAD).json()

    response = client.get(f"/api/v1/catalog/categories/{created['id']}")

    assert response.status_code == 200


def test_get_category_not_found_returns_404(client: TestClient) -> None:
    response = client.get(f"/api/v1/catalog/categories/{uuid.uuid4()}")

    assert response.status_code == 404


def test_update_category_returns_200(client: TestClient) -> None:
    created = client.post("/api/v1/catalog/categories", json=CATEGORY_PAYLOAD).json()

    response = client.patch(
        f"/api/v1/catalog/categories/{created['id']}", json={"name": "Updated"}
    )

    assert response.status_code == 200


def test_delete_category_returns_204(client: TestClient) -> None:
    created = client.post("/api/v1/catalog/categories", json=CATEGORY_PAYLOAD).json()

    response = client.delete(f"/api/v1/catalog/categories/{created['id']}")

    assert response.status_code == 204


def test_list_root_categories_returns_200(client: TestClient) -> None:
    response = client.get("/api/v1/catalog/categories")

    assert response.status_code == 200


def test_list_category_children_returns_200(client: TestClient) -> None:
    parent = client.post("/api/v1/catalog/categories", json=CATEGORY_PAYLOAD).json()

    response = client.get(f"/api/v1/catalog/categories/{parent['id']}/children")

    assert response.status_code == 200


# ---------------------------------------------------------------------------
# Brands
# ---------------------------------------------------------------------------


def test_create_brand_returns_201(client: TestClient) -> None:
    response = client.post("/api/v1/catalog/brands", json=BRAND_PAYLOAD)

    assert response.status_code == 201


def test_create_brand_conflict_returns_409(client: TestClient) -> None:
    client.post("/api/v1/catalog/brands", json=BRAND_PAYLOAD)
    response = client.post("/api/v1/catalog/brands", json=BRAND_PAYLOAD)

    assert response.status_code == 409


def test_get_brand_returns_200(client: TestClient) -> None:
    created = client.post("/api/v1/catalog/brands", json=BRAND_PAYLOAD).json()

    response = client.get(f"/api/v1/catalog/brands/{created['id']}")

    assert response.status_code == 200


def test_get_brand_not_found_returns_404(client: TestClient) -> None:
    response = client.get(f"/api/v1/catalog/brands/{uuid.uuid4()}")

    assert response.status_code == 404


def test_update_brand_returns_200(client: TestClient) -> None:
    created = client.post("/api/v1/catalog/brands", json=BRAND_PAYLOAD).json()

    response = client.patch(
        f"/api/v1/catalog/brands/{created['id']}", json={"name": "Updated"}
    )

    assert response.status_code == 200


def test_delete_brand_returns_204(client: TestClient) -> None:
    created = client.post("/api/v1/catalog/brands", json=BRAND_PAYLOAD).json()

    response = client.delete(f"/api/v1/catalog/brands/{created['id']}")

    assert response.status_code == 204


# ---------------------------------------------------------------------------
# Products
# ---------------------------------------------------------------------------


def test_create_product_returns_201(client: TestClient) -> None:
    response = client.post("/api/v1/catalog/products", json=PRODUCT_PAYLOAD)

    assert response.status_code == 201


def test_create_product_conflict_returns_409(client: TestClient) -> None:
    client.post("/api/v1/catalog/products", json=PRODUCT_PAYLOAD)
    response = client.post("/api/v1/catalog/products", json=PRODUCT_PAYLOAD)

    assert response.status_code == 409


def test_get_product_returns_200(client: TestClient) -> None:
    created = client.post("/api/v1/catalog/products", json=PRODUCT_PAYLOAD).json()

    response = client.get(f"/api/v1/catalog/products/{created['id']}")

    assert response.status_code == 200


def test_get_product_not_found_returns_404(client: TestClient) -> None:
    response = client.get(f"/api/v1/catalog/products/{uuid.uuid4()}")

    assert response.status_code == 404


def test_update_product_returns_200(client: TestClient) -> None:
    created = client.post("/api/v1/catalog/products", json=PRODUCT_PAYLOAD).json()

    response = client.patch(
        f"/api/v1/catalog/products/{created['id']}", json={"name": "Updated"}
    )

    assert response.status_code == 200


def test_delete_product_returns_204(client: TestClient) -> None:
    created = client.post("/api/v1/catalog/products", json=PRODUCT_PAYLOAD).json()

    response = client.delete(f"/api/v1/catalog/products/{created['id']}")

    assert response.status_code == 204


def test_list_brand_products_returns_200(client: TestClient) -> None:
    brand = client.post("/api/v1/catalog/brands", json=BRAND_PAYLOAD).json()

    response = client.get(f"/api/v1/catalog/brands/{brand['id']}/products")

    assert response.status_code == 200


def test_list_category_products_returns_200(client: TestClient) -> None:
    category = client.post("/api/v1/catalog/categories", json=CATEGORY_PAYLOAD).json()

    response = client.get(f"/api/v1/catalog/categories/{category['id']}/products")

    assert response.status_code == 200


# ---------------------------------------------------------------------------
# Variants
# ---------------------------------------------------------------------------


def test_create_variant_returns_201(client: TestClient) -> None:
    product = client.post("/api/v1/catalog/products", json=PRODUCT_PAYLOAD).json()

    response = client.post(
        f"/api/v1/catalog/products/{product['id']}/variants",
        json={"sku": "VAR-001", "price": "4.99", "attributes": {}},
    )

    assert response.status_code == 201


def test_create_variant_conflict_returns_409(client: TestClient) -> None:
    product = client.post("/api/v1/catalog/products", json=PRODUCT_PAYLOAD).json()
    payload = {"sku": "VAR-001", "price": "4.99", "attributes": {}}
    client.post(f"/api/v1/catalog/products/{product['id']}/variants", json=payload)

    response = client.post(
        f"/api/v1/catalog/products/{product['id']}/variants", json=payload
    )

    assert response.status_code == 409


def test_get_variant_returns_200(client: TestClient) -> None:
    product = client.post("/api/v1/catalog/products", json=PRODUCT_PAYLOAD).json()
    variant = client.post(
        f"/api/v1/catalog/products/{product['id']}/variants",
        json={"sku": "VAR-001", "price": "4.99", "attributes": {}},
    ).json()

    response = client.get(
        f"/api/v1/catalog/products/{product['id']}/variants/{variant['id']}"
    )

    assert response.status_code == 200


def test_get_variant_not_found_returns_404(client: TestClient) -> None:
    product = client.post("/api/v1/catalog/products", json=PRODUCT_PAYLOAD).json()

    response = client.get(
        f"/api/v1/catalog/products/{product['id']}/variants/{uuid.uuid4()}"
    )

    assert response.status_code == 404


def test_list_product_variants_returns_200(client: TestClient) -> None:
    product = client.post("/api/v1/catalog/products", json=PRODUCT_PAYLOAD).json()

    response = client.get(f"/api/v1/catalog/products/{product['id']}/variants")

    assert response.status_code == 200


def test_delete_variant_returns_204(client: TestClient) -> None:
    product = client.post("/api/v1/catalog/products", json=PRODUCT_PAYLOAD).json()
    variant = client.post(
        f"/api/v1/catalog/products/{product['id']}/variants",
        json={"sku": "VAR-001", "price": "4.99", "attributes": {}},
    ).json()

    response = client.delete(
        f"/api/v1/catalog/products/{product['id']}/variants/{variant['id']}"
    )

    assert response.status_code == 204


# ---------------------------------------------------------------------------
# Category Attributes
# ---------------------------------------------------------------------------


def test_create_attribute_returns_201(client: TestClient) -> None:
    category = client.post("/api/v1/catalog/categories", json=CATEGORY_PAYLOAD).json()

    response = client.post(
        f"/api/v1/catalog/categories/{category['id']}/attributes",
        json={"key": "color", "value_type": "string", "required": False},
    )

    assert response.status_code == 201


def test_create_attribute_conflict_returns_409(client: TestClient) -> None:
    category = client.post("/api/v1/catalog/categories", json=CATEGORY_PAYLOAD).json()
    payload = {"key": "color", "value_type": "string", "required": False}
    client.post(f"/api/v1/catalog/categories/{category['id']}/attributes", json=payload)

    response = client.post(
        f"/api/v1/catalog/categories/{category['id']}/attributes", json=payload
    )

    assert response.status_code == 409


def test_get_attribute_returns_200(client: TestClient) -> None:
    category = client.post("/api/v1/catalog/categories", json=CATEGORY_PAYLOAD).json()
    attr = client.post(
        f"/api/v1/catalog/categories/{category['id']}/attributes",
        json={"key": "color", "value_type": "string", "required": False},
    ).json()

    response = client.get(
        f"/api/v1/catalog/categories/{category['id']}/attributes/{attr['id']}"
    )

    assert response.status_code == 200


def test_get_attribute_not_found_returns_404(client: TestClient) -> None:
    category = client.post("/api/v1/catalog/categories", json=CATEGORY_PAYLOAD).json()

    response = client.get(
        f"/api/v1/catalog/categories/{category['id']}/attributes/{uuid.uuid4()}"
    )

    assert response.status_code == 404


def test_list_category_attributes_returns_200(client: TestClient) -> None:
    category = client.post("/api/v1/catalog/categories", json=CATEGORY_PAYLOAD).json()

    response = client.get(f"/api/v1/catalog/categories/{category['id']}/attributes")

    assert response.status_code == 200


def test_delete_attribute_returns_204(client: TestClient) -> None:
    category = client.post("/api/v1/catalog/categories", json=CATEGORY_PAYLOAD).json()
    attr = client.post(
        f"/api/v1/catalog/categories/{category['id']}/attributes",
        json={"key": "color", "value_type": "string", "required": False},
    ).json()

    response = client.delete(
        f"/api/v1/catalog/categories/{category['id']}/attributes/{attr['id']}"
    )

    assert response.status_code == 204
