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

Never patch internals. Pass test implementations through the same constructor path used in production. Never use `__new__` to bypass `__init__` — if a service cannot be constructed with fakes through its constructor, the service needs to be refactored to accept its dependencies directly.

Use a private builder function in the test module to construct services with injected fakes. Accept pre-populated data as optional arguments to keep individual tests minimal.

```python
def _category_service(categories: list | None = None) -> CategoryService:
    return CategoryService(
        repo=FakeCategoryRepository(categories),
        audit=FakeAuditPort(),
        broker=NoOpMessageBroker(),
    )


def test_raises_if_not_found() -> None:
    svc = _category_service()

    with pytest.raises(CategoryNotFound):
        svc.get(uuid.uuid4())
```

## 4. Build model instances with `make_*` functions

Use a `make_<model>` function in `fakes.py` to construct model instances for tests. Each function accepts `**kwargs` and provides a sensible default for every field so individual tests only specify what is relevant to the case being tested.

Instantiate the model directly and assign fields one by one:

```python
def make_customer(**kwargs: object) -> Customer:
    """Build a Customer instance with sensible defaults for testing."""
    customer = Customer()
    customer.id = kwargs.get("id", uuid.uuid4())
    customer.email = kwargs.get("email", "test@example.com")
    customer.first_name = kwargs.get("first_name", "Jane")
    customer.deleted_at = kwargs.get("deleted_at")
    customer.created_at = kwargs.get("created_at", datetime.now(UTC))
    return customer
```

`deleted_at` defaults to `None` (active record). Tests that need a soft-deleted record pass `deleted_at=datetime.now(UTC)` explicitly.

Fake repository `create()` methods reuse the domain's own `make_*` function rather than duplicating field assignment:

```python
def create(self, **kwargs: object) -> Customer:
    customer = make_customer(**kwargs)
    self._store[customer.id] = customer
    return customer
```

## 5. Write route tests using the test client

Route tests verify that the endpoint is wired correctly — the right handler is reached, the right status code is returned, the response body is correctly shaped, and error mapping works. Business logic belongs in the service tests.

Every endpoint requires two kinds of tests:

- A smoke test that asserts only the status code. Smoke tests are prefixed with `test_smoke_` so they are immediately identifiable by name and can be targeted with `-k smoke`.
- A body test that asserts the key fields of the response body on the happy path.

Error path tests (404, 409, 400) are not smoke tests — name them descriptively and assert both the status code and the `error.code` field in the response body.

Define request payloads using `make_<payload>` factory functions with Faker-generated defaults. Each function accepts `**kwargs` so individual tests can pin specific fields they care about:

```python
fake = Faker()


def make_product_payload(**kwargs: object) -> dict[str, object]:
    """Build a valid create-product request payload with randomised defaults."""
    return {
        "sku": fake.bothify("SKU-###"),
        "name": fake.word(),
        "base_price": "9.99",
        **kwargs,
    }
```

This keeps tests independent from each other — no shared state, no risk of one test's data affecting another. Inline literals are acceptable when a test asserts a specific value and co-location makes the intent clearer (e.g. `json={"name": "Updated"}` paired with `assert data["name"] == "Updated"`).

```python
PRODUCT_PAYLOAD = {"sku": "SKU-001", "name": "Widget", "base_price": "9.99"}


def test_smoke_create_product(client: TestClient) -> None:
    response = client.post("/api/v1/catalog/products", json=PRODUCT_PAYLOAD)

    assert response.status_code == 201


def test_create_product_returns_expected_body(client: TestClient) -> None:
    data = client.post("/api/v1/catalog/products", json=PRODUCT_PAYLOAD).json()

    assert data["sku"] == PRODUCT_PAYLOAD["sku"]
    assert data["name"] == PRODUCT_PAYLOAD["name"]


def test_create_product_conflict_returns_409(client: TestClient) -> None:
    client.post("/api/v1/catalog/products", json=PRODUCT_PAYLOAD)
    response = client.post("/api/v1/catalog/products", json=PRODUCT_PAYLOAD)

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "PRODUCT_ALREADY_EXISTS"


def test_get_product_not_found_returns_404(client: TestClient) -> None:
    response = client.get(f"/api/v1/catalog/products/{uuid.uuid4()}")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "PRODUCT_NOT_FOUND"
```

## 6. Simulate integrity errors with a raising repository

To test that a service correctly handles database constraint violations, define a private `_IntegrityErrorOnWrite` mixin in `fakes.py` that overrides `create()` and `update()` to raise `IntegrityError`. Concrete classes combine the mixin with the relevant fake repository, with the mixin listed first so its methods take precedence.

```python
class _IntegrityErrorOnWrite:
    """Mixin that raises IntegrityError on create and update."""

    def _raise(self) -> None:
        raise IntegrityError(None, None, Exception("unique constraint"))

    def create(self, **kwargs: Any) -> Any:  # type: ignore[override]
        self._raise()

    def update(self, record: Any, data: Any) -> Any:  # type: ignore[override]
        self._raise()


class IntegrityErrorProductRepository(_IntegrityErrorOnWrite, FakeProductRepository):
    pass
```

In the test, pass the raising repository directly to the service builder:

```python
def test_raises_on_duplicate_sku(self) -> None:
    service = _product_service(repo=IntegrityErrorProductRepository())

    with pytest.raises(ProductAlreadyExists):
        service.create(sku="SKU-001", ...)
```

## 7. Structure `conftest.py` consistently

`conftest.py` is the only place for pytest fixtures shared across test files in a domain. Every domain with a route layer has at least these fixtures, in this order:

- `setup_schema` — `scope="session"`, `autouse=True`. Creates all tables once per session via `BaseModel.metadata.create_all(engine)`.
- `app` — constructs the domain's FastAPI app wired to the test database. Overrides `_db_dependency` and `_auth_dependency` so route tests run without real auth or a production database.
- `clean_tables` — `autouse=True`. Truncates all domain tables between tests using `TRUNCATE ... RESTART IDENTITY CASCADE`. List tables in dependency order (children before parents) to avoid FK violations.
- `client` — returns a `TestClient` wrapping the `app` fixture.

Add further fixtures as the domain requires. The baseline above applies to any domain that exposes HTTP endpoints.

## 8. Group test classes by service

One class per service method, named `Test<Service><Method>`:

```python
class TestCategoryServiceCreate: ...


class TestCategoryServiceGet: ...


class TestCategoryServiceUpdate: ...
```

Classes for the same service are grouped together. Each group is preceded by a section separator:

```python
# ---------------------------------------------------------------------------
# CategoryService
# ---------------------------------------------------------------------------


class TestCategoryServiceCreate: ...
```

Two blank lines separate the separator from the first class (standard PEP 8 between top-level definitions). Two blank lines also separate each group from the next separator.

## 9. Place shared test utilities inside the domain's `tests/` directory

Fixtures, fakes, and factories live inside the domain they support.

```
app/catalog/tests/
├── conftest.py    # pytest fixtures
├── fakes.py       # FakeProductRepository, etc.
└── factories.py   # ProductFactory, etc.
```

Production code must never import from a `tests/` directory.

## 10. What not to test

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


## 11. Group related cases with subtests

When a test function covers multiple input/output variations of the same behavior, use `pytest-subtests` instead of separate test functions. Each subtest runs independently, so a single failure does not mask the others.

```python
def test_sanitizes_strings(subtests: pytest.Subtests) -> None:
    cases = [
        ("strips newline", "foo\nbar", "foobar"),
        ("strips carriage return", "foo\rbar", "foobar"),
        ("strips both", "foo\r\nbar", "foobar"),
    ]
    for description, value, expected in cases:
        with subtests.test(description):
            assert _Schema(name=value).name == expected
```

Use separate test functions when the cases test meaningfully different behaviors or require different setup.
