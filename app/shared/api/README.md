# api

Provides the platform-wide HTTP response envelope, pagination primitives, and input
sanitization utilities. All domain routes must use these types — never define custom
response wrappers or pagination logic in a domain module.

## Package layout

```
api/
├── __init__.py     # Package entry point
├── schemas.py      # Response and error envelope contracts
├── pagination.py   # Keyset pagination layer
└── validators.py   # Input sanitization layer
```

## Public API

### Response types

| Type | Use |
| --- | --- |
| `DataResponse[T]` | Envelope for a single-resource response |
| `PaginatedResponse[T]` | Envelope for a paginated collection response |
| `PaginationMeta` | Cursor and `has_more` metadata attached to `PaginatedResponse` |
| `ErrorResponse` | Envelope for all error responses |
| `RequestContext` | Typed base for extracting path params, query params, and headers from a `Request` |

Use `error_response(code, message)` to produce a serialized dict ready for `JSONResponse`
without instantiating `ErrorResponse` manually.

### Pagination

| Symbol | Description |
| --- | --- |
| `paginate(rows, page_size, to_response, get_cursor_fields)` | Builds a `PaginatedResponse` from a `limit + 1` query result |
| `encode_cursor(created_at, record_id)` | Encodes a `(created_at, id)` pair as an opaque base64 cursor |
| `decode_cursor(cursor)` | Decodes a cursor back to `(datetime, UUID)` |

`paginate()` expects the repository to return `page_size + 1` rows. It trims the extra
row, sets `has_more`, and encodes the next cursor automatically.

```python
from app.shared.api import decode_cursor, paginate

PAGE_SIZE = 20


@router.get("/products")
def list_products(
    db: DbDep, cursor: str | None = None
) -> PaginatedResponse[ProductResponse]:
    decoded = decode_cursor(cursor) if cursor else None
    rows = repo.list_page(limit=PAGE_SIZE + 1, cursor=decoded)
    return paginate(
        rows=rows,
        page_size=PAGE_SIZE,
        to_response=lambda r: ProductResponse.model_validate(r, from_attributes=True),
        get_cursor_fields=lambda r: (r.created_at, r.id),
    )
```

### String sanitization

`sanitize_strings(*fields)` returns a Pydantic `field_validator` that strips `\n` and
`\r` from the named fields to prevent log injection. Assign the result to `_strip` on
any request schema.

```python
from app.shared.api import sanitize_strings


class CreateProductRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str = Field(min_length=1, max_length=1000)

    _strip = sanitize_strings("name", "description")
```

### RequestContext

Subclass `RequestContext` to extract and coerce typed values from a FastAPI `Request`
without accessing `request.path_params` or `request.query_params` directly in the
route handler.

```python
from app.shared.api import RequestContext


class ProductPathParams(BaseModel):
    product_id: uuid.UUID


class ProductContext(RequestContext):
    path_params: ProductPathParams


@router.get("/products/{product_id}")
def get_product(request: Request) -> ProductResponse:
    ctx = ProductContext.model_validate({"request": request})
    product_id = ctx.path_params.product_id
    ...
```
