# Writing Tests

How to write tests in this project consistently across all domains.

See [ADR-010: Testability by Design](../adr/010-testability-by-design.md) for the architectural rationale.

---

## 1. Locate the test file

Tests live inside the domain they test, under `app/<domain>/tests/`.

```
app/catalog/service.py        → app/catalog/tests/test_service.py
app/catalog/routes.py         → app/catalog/tests/test_routes.py
app/shared/events/envelope.py → app/shared/tests/events/test_envelope.py
```

## 2. Use the correct test layer

| What you are testing | Layer | DB access | HTTP client |
| --- | --- | --- | --- |
| Domain / use case logic | Unit | No | No |
| Repository | Integration | Yes | No |
| Route handler | Integration | Yes | Yes |

Pure logic (services, domain rules) must be tested without DB access.

## 3. Inject dependencies explicitly

Never patch internals. Pass test implementations through the same injection path used in production.

```python
def test_creates_product() -> None:
    repo = FakeProductRepository()
    service = ProductService(repository=repo)

    product = service.create(name="Headphones", price=99)

    assert repo.saved == [product]
```

## 4. Write route smoke tests using the test client

Every endpoint must have at least one smoke test.

```python
def test_create_product_returns_201(client: TestClient) -> None:
    response = client.post("/products", json={"name": "Headphones", "price": 99})

    assert response.status_code == 201
```

## 5. Place shared test utilities inside the domain's `tests/` directory

Fixtures, fakes, and factories live inside the domain they support.

```
app/catalog/tests/
├── conftest.py    # pytest fixtures
├── fakes.py       # FakeProductRepository, etc.
└── factories.py   # ProductFactory, etc.
```

Production code must never import from a `tests/` directory.

## 6. What not to test

**Framework behavior** — do not test what FastAPI, SQLAlchemy, or Pydantic already guarantee.

```python
# wrong — tests Pydantic, not your code
def test_name_is_required() -> None:
    with pytest.raises(ValidationError):
        CreateProductRequest(price=99)
```

**Implementation details** — do not test private methods, internal state, or how something works. Test what a component produces, not how it produces it.

```python
# wrong — tests internal state
def test_repository_uses_correct_query() -> None:
    assert repo._last_query == "SELECT ..."
```

**Infrastructure behavior** — do not test that the database persists data, that the message broker delivers events, or that external APIs respond. Those are the infrastructure's responsibility.

```python
# wrong — tests the database, not your code
def test_product_is_saved_in_db() -> None:
    db.add(product)
    db.commit()
    assert db.query(Product).count() == 1
```

