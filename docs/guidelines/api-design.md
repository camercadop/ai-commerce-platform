# API Design

How to design and implement API endpoints consistently across all domains.

See [ADR-002: API-First Design](../adr/002-api-first-design.md) and
[ADR-014: Uniform Interface Contract](../adr/014-uniform-interface-contract.md) for the architectural rationale.

---

## 1. Define the contract before the implementation

Every endpoint must have a request schema and a response schema defined in `schemas.py`
before the route handler is written.

```python
# schemas.py
class CreateProductRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    price: Decimal = Field(gt=0)

class ProductResponse(BaseModel):
    id: UUID
    name: str
    price: Decimal
```

## 2. Use the uniform response envelope

All responses must be wrapped in the platform envelope from `shared/api/`.

```python
# success
{"data": {...}}

# error
{"error": {"code": "PRODUCT_NOT_FOUND", "message": "..."}}

# paginated
{"data": [...], "pagination": {"next_cursor": "...", "has_more": true}}
```

## 3. Version all routes

All routes are prefixed with `/api/v1/`. The version starts at `v1` and increments
only when a breaking change to an existing contract is required. Non-breaking additions
(new optional fields, new endpoints) do not require a new version.

```python
router = APIRouter(prefix="/api/v1/products")
```

## 4. Validate and sanitize in schemas, not in route handlers

All validation and sanitization lives in Pydantic schemas. Route handlers use
already-validated fields directly.

```python
class CreateProductRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)

    @field_validator("name")
    @classmethod
    def strip_control_characters(cls, v: str) -> str:
        return v.replace("\n", "").replace("\r", "")
```

## 5. Use cursor-based pagination on collection endpoints

All collection endpoints use cursor-based pagination. Offset-based pagination is not
supported. Every collection endpoint must declare a page size limit and signal when
results have been bounded (ADR-012).

```python
class ProductListRequest(BaseModel):
    cursor: str | None = None
    limit: int = Field(default=20, ge=1, le=100)
```

The cursor is opaque to the consumer. The response always includes `next_cursor` and
`has_more` so the consumer can determine whether more results exist.

## 6. Declare `response_model` on every route decorator

Every route must declare its `response_model` explicitly. This enforces the contract
at the framework level and prevents internal fields from leaking into responses.

```python
@router.post("/", response_model=ProductResponse, status_code=201)
def create_product(body: CreateProductRequest) -> ProductResponse:
    ...
```

## 7. Keep route handlers thin

A route handler must only parse the request, call the service, and return the response.
No business logic belongs in a route handler.

```python
@router.post("/", response_model=ProductResponse, status_code=201)
def create_product(
    body: CreateProductRequest,
    service: ProductService = Depends(get_product_service),
) -> ProductResponse:
    return service.create(body)
```

## 8. Inject the database session via `Depends(get_db)`

The database session is always injected through FastAPI's dependency injection. It must
never be instantiated directly inside a route handler or service.

```python
def get_db() -> Generator[Session, None, None]:
    with SessionLocal() as session:
        yield session

@router.post("/", response_model=ProductResponse, status_code=201)
def create_product(
    body: CreateProductRequest,
    db: Session = Depends(get_db),
) -> ProductResponse:
    ...
```

## 9. Use explicit HTTP status codes

| Situation | Status code |
| --- | --- |
| Resource created | `201` |
| Successful read / update | `200` |
| Accepted async operation | `202` |
| Validation error | `422` |
| Not found | `404` |
| Unauthorized | `401` |
| Forbidden | `403` |
| Conflict / duplicate | `409` |

---

## Rules

- Every endpoint must have a published contract (request + response schema) before implementation.
- All responses must use the platform envelope from `shared/api/`.
- All routes must be prefixed with `/api/v1/`. Increment the version only on breaking changes.
- All validation and sanitization must live in Pydantic schemas — never in route handlers.
- All collection endpoints must use cursor-based pagination and signal bounded results.
- Every route decorator must declare `response_model` explicitly.
- Route handlers must only parse the request, call the service, and return the response — no business logic.
- The database session must always be injected via `Depends(get_db)` — never instantiated directly.
- No internal model, database schema, or SQLAlchemy model may be exposed directly in a response.
