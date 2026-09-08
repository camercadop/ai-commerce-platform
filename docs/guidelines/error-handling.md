# Error Handling

How to declare failure modes, structure exceptions, and write retry logic across all
domains.

See [ADR-008: Explicit Failure Handling](../adr/008-explicit-failure-handling.md) and
[ADR-012: Bounded Operations](../adr/012-bounded-operations.md) for the architectural
rationale.

---

## 1. Define domain exceptions in `exceptions.py`

Every domain must declare its own exception hierarchy in `exceptions.py`. Exceptions
must be specific enough for callers to distinguish failure modes without inspecting
messages or internal state.

```python
# app/catalog/exceptions.py


class CatalogError(Exception):
    """Base exception for the catalog domain."""

    code: str


class ProductNotFound(CatalogError):
    """Raised when a product does not exist."""

    code = "PRODUCT_NOT_FOUND"

    def __init__(self, product_id: UUID) -> None:
        self.product_id = product_id
        super().__init__(f"Product not found: {product_id}")


class ProductAlreadyExists(CatalogError):
    """Raised when creating a product with a name that is already taken."""

    code = "PRODUCT_ALREADY_EXISTS"

    def __init__(self, name: str) -> None:
        self.name = name
        super().__init__(f"Product already exists: {name}")
```

Each domain has a base exception (e.g. `CatalogError`) so callers can catch the entire
domain's failures as a group when needed.

## 2. Raise domain exceptions from services, not HTTP exceptions

Services raise domain exceptions. They must never import or raise `HTTPException` —
that is the route layer's responsibility.

```python
# app/catalog/service.py


class ProductService:
    """Manages product lifecycle operations."""

    def get(self, product_id: UUID) -> Product:
        """Return the product with the given ID.

        Raises:
            ProductNotFound: If no product with the given ID exists.
        """
        product = self.repository.find(product_id)
        if product is None:
            raise ProductNotFound(product_id)
        return product
```

## 3. Map domain exceptions to HTTP responses in a handler

Register a single exception handler per domain exception in the domain's `routes.py`
or a dedicated `handlers.py`. This keeps the mapping in one place and out of individual
route functions.

```python
# app/catalog/routes.py

from fastapi import Request
from fastapi.responses import JSONResponse


def register_exception_handlers(app: FastAPI) -> None:
    """Register catalog domain exception handlers."""

    @app.exception_handler(ProductNotFound)
    def handle_product_not_found(
        request: Request, exc: ProductNotFound
    ) -> JSONResponse:
        return JSONResponse(
            status_code=404,
            content={"error": {"code": exc.code, "message": str(exc)}},
        )

    @app.exception_handler(ProductAlreadyExists)
    def handle_product_already_exists(
        request: Request, exc: ProductAlreadyExists
    ) -> JSONResponse:
        return JSONResponse(
            status_code=409,
            content={"error": {"code": exc.code, "message": str(exc)}},
        )
```

Route handlers stay clean — they never catch exceptions themselves:

```python
@router.get("/{product_id}", response_model=ProductResponse)
def get_product(
    product_id: UUID,
    service: ProductService = Depends(get_product_service),
) -> ProductResponse:
    return service.get(product_id)
```

## 4. Never swallow exceptions

Every `except` block must either re-raise or surface the failure explicitly to the
caller. Logging and swallowing is not permitted.

```python
# wrong — failure is hidden from the caller
try:
    result = external_client.fetch(resource_id)
except ExternalServiceError:
    logger.error("External service failed")
    return None

# correct — failure is surfaced explicitly
try:
    result = external_client.fetch(resource_id)
except ExternalServiceError as exc:
    raise ExternalResourceUnavailable(resource_id) from exc
```

## 5. Declare fallback behavior explicitly

If a fallback is appropriate, it must be visible to the caller — never applied silently.
Return a typed result that signals the fallback occurred, or raise a distinct exception.

```python
# wrong — caller cannot tell this is a fallback
def get_price(product_id: UUID) -> Decimal:
    try:
        return pricing_service.get(product_id)
    except PricingUnavailable:
        return Decimal("0.00")


# correct — fallback is explicit and visible
def get_price(product_id: UUID) -> Decimal | None:
    """Return the current price, or None if the pricing service is unavailable.

    Callers must handle the None case explicitly.
    """
    try:
        return pricing_service.get(product_id)
    except PricingUnavailable:
        logger.warning("Pricing service unavailable for product: %s", product_id)
        return None
```

## 6. Bound all retry logic explicitly

Retry logic must declare its maximum attempt count and the conditions under which it
retries. Open-ended retry loops are not permitted.

```python
# wrong — unbounded, retries on any exception
while True:
    try:
        return client.call()
    except Exception:
        time.sleep(1)

# correct — bounded, retries only on the expected transient failure
MAX_ATTEMPTS = 3

for attempt in range(1, MAX_ATTEMPTS + 1):
    try:
        return client.call()
    except TransientServiceError:
        if attempt == MAX_ATTEMPTS:
            raise
        time.sleep(2**attempt)
```

Document the retry bounds in the method's docstring:

```python
def fetch_with_retry(resource_id: UUID) -> Resource:
    """Fetch the resource, retrying up to 3 times on transient failures.

    Raises:
        TransientServiceError: If all 3 attempts fail.
        ResourceNotFound: If the resource does not exist (not retried).
    """
```

## 7. Use `from exc` when wrapping exceptions

When catching a low-level exception and raising a domain one, always chain them with
`raise ... from exc` to preserve the original traceback.

```python
try:
    row = db.execute(query)
except SQLAlchemyError as exc:
    raise ProductRepositoryError("Failed to fetch product") from exc
```

