import logging
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.catalog.exceptions import CatalogError
from app.catalog.repository import (
    BrandRepository,
    CategoryAttributeRepository,
    CategoryRepository,
    ProductRepository,
    VariantRepository,
)
from app.catalog.schemas import (
    BrandResponse,
    CategoryAttributeResponse,
    CategoryResponse,
    CreateBrandRequest,
    CreateCategoryAttributeRequest,
    CreateCategoryRequest,
    CreateProductRequest,
    CreateVariantRequest,
    ProductResponse,
    UpdateBrandRequest,
    UpdateCategoryAttributeRequest,
    UpdateCategoryRequest,
    UpdateProductRequest,
    UpdateVariantRequest,
    VariantResponse,
)
from app.catalog.service import (
    PAGE_SIZE,
    BrandService,
    CategoryAttributeService,
    CategoryService,
    ProductService,
    VariantService,
)
from app.shared.api import (
    RequestContext,
    decode_cursor,
    error_response,
    paginate,
)
from app.shared.api.schemas import PaginatedResponse
from app.shared.audit_log import AuditPort
from app.shared.auth import TokenClaims
from app.shared.events import MessageBroker

logger = logging.getLogger(__name__)

CATEGORIES_PREFIX = "/api/v1/catalog/categories"
BRANDS_PREFIX = "/api/v1/catalog/brands"
PRODUCTS_PREFIX = "/api/v1/catalog/products"


def _db_dependency() -> Session:
    """Sentinel dependency overridden at application startup via dependency_overrides.

    Never called directly. app.py replaces this with make_get_db(session_factory)
    so FastAPI can introspect a zero-argument signature at import time.
    """
    raise NotImplementedError  # pragma: no cover


def _auth_dependency() -> TokenClaims:
    """Sentinel dependency overridden at application startup via dependency_overrides.

    Never called directly. app.py replaces this with the JWT validator dependency
    built from AuthSettings.
    """
    raise NotImplementedError  # pragma: no cover


def _audit_dependency() -> AuditPort:
    """Sentinel dependency overridden at application startup via dependency_overrides.

    Never called directly. app.py replaces this with the resolved singleton from
    CatalogContainer.
    """
    raise NotImplementedError  # pragma: no cover


def _broker_dependency() -> MessageBroker:
    """Sentinel dependency overridden at application startup via dependency_overrides.

    Never called directly. app.py replaces this with the resolved singleton from
    CatalogContainer.
    """
    raise NotImplementedError  # pragma: no cover


DbDep = Annotated[Session, Depends(_db_dependency)]
AuthDep = Annotated[TokenClaims, Depends(_auth_dependency)]
AuditDep = Annotated[AuditPort, Depends(_audit_dependency)]
BrokerDep = Annotated[MessageBroker, Depends(_broker_dependency)]


# ---------------------------------------------------------------------------
# RequestContext subclasses for nested resources
# ---------------------------------------------------------------------------


class _ProductPathParams(BaseModel):
    """Typed path params for routes nested under a product."""

    product_id: uuid.UUID


class _CategoryPathParams(BaseModel):
    """Typed path params for routes nested under a category."""

    category_id: uuid.UUID


class VariantRequestContext(RequestContext):
    """RequestContext for variant routes — provides typed product_id path param.

    Use model_validate({'request': request}) to get a coerced instance.
    """

    @property
    def path_params(self) -> _ProductPathParams:  # type: ignore[override]
        """Return typed path params coerced from the request."""
        return _ProductPathParams.model_validate(dict(self.request.path_params))


class AttributeRequestContext(RequestContext):
    """RequestContext for category attribute routes.

    Provides typed category_id path param. Use model_validate({'request': request})
    to get a coerced instance.
    """

    @property
    def path_params(self) -> _CategoryPathParams:  # type: ignore[override]
        """Return typed path params coerced from the request."""
        return _CategoryPathParams.model_validate(dict(self.request.path_params))


# ---------------------------------------------------------------------------
# Response mappers
# ---------------------------------------------------------------------------


def _to_category(obj: object) -> CategoryResponse:
    return CategoryResponse.model_validate(obj, from_attributes=True)


def _to_brand(obj: object) -> BrandResponse:
    return BrandResponse.model_validate(obj, from_attributes=True)


def _to_product(obj: object) -> ProductResponse:
    return ProductResponse.model_validate(obj, from_attributes=True)


def _to_variant(obj: object) -> VariantResponse:
    return VariantResponse.model_validate(obj, from_attributes=True)


def _to_attribute(obj: object) -> CategoryAttributeResponse:
    return CategoryAttributeResponse.model_validate(obj, from_attributes=True)


# ---------------------------------------------------------------------------
# Service dependency factories
# ---------------------------------------------------------------------------


def _get_category_service(
    db: DbDep,
    audit: AuditDep,
    broker: BrokerDep,
) -> CategoryService:
    """FastAPI dependency that builds a CategoryService for the current request."""
    return CategoryService(CategoryRepository(db), audit, broker)


def _get_brand_service(
    db: DbDep,
    audit: AuditDep,
    broker: BrokerDep,
) -> BrandService:
    """FastAPI dependency that builds a BrandService for the current request."""
    return BrandService(BrandRepository(db), audit, broker)


def _get_product_service(
    db: DbDep,
    audit: AuditDep,
    broker: BrokerDep,
) -> ProductService:
    """FastAPI dependency that builds a ProductService for the current request."""
    return ProductService(
        ProductRepository(db),
        CategoryRepository(db),
        BrandRepository(db),
        audit,
        broker,
    )


def _get_variant_service(
    db: DbDep,
    audit: AuditDep,
    broker: BrokerDep,
) -> VariantService:
    """FastAPI dependency that builds a VariantService for the current request."""
    return VariantService(
        VariantRepository(db),
        ProductRepository(db),
        CategoryRepository(db),
        CategoryAttributeRepository(db),
        audit,
        broker,
    )


def _get_attribute_service(
    db: DbDep,
    audit: AuditDep,
    broker: BrokerDep,
) -> CategoryAttributeService:
    """FastAPI dependency that builds a CategoryAttributeService for the current request."""  # noqa: E501
    return CategoryAttributeService(
        CategoryAttributeRepository(db),
        CategoryRepository(db),
        audit,
        broker,
    )


CategoryServiceDep = Annotated[CategoryService, Depends(_get_category_service)]
BrandServiceDep = Annotated[BrandService, Depends(_get_brand_service)]
ProductServiceDep = Annotated[ProductService, Depends(_get_product_service)]
VariantServiceDep = Annotated[VariantService, Depends(_get_variant_service)]
AttributeServiceDep = Annotated[
    CategoryAttributeService, Depends(_get_attribute_service)
]


# ---------------------------------------------------------------------------
# Category routes
# ---------------------------------------------------------------------------

category_router = APIRouter()


@category_router.post(
    CATEGORIES_PREFIX, response_model=CategoryResponse, status_code=201
)
def create_category(
    body: CreateCategoryRequest,
    claims: AuthDep,
    db: DbDep,
    service: CategoryServiceDep,
) -> CategoryResponse:
    """Create a new category."""
    result = _to_category(
        service.create(
            actor_id=claims.actor_id(),
            name=body.name,
            description=body.description,
            parent_id=body.parent_id,
        )
    )
    db.commit()
    return result


@category_router.get(
    f"{CATEGORIES_PREFIX}/{{category_id}}", response_model=CategoryResponse
)
def get_category(
    category_id: uuid.UUID,
    service: CategoryServiceDep,
) -> CategoryResponse:
    """Return the category with the given id."""
    return _to_category(service.get(category_id))


@category_router.patch(
    f"{CATEGORIES_PREFIX}/{{category_id}}", response_model=CategoryResponse
)
def update_category(
    category_id: uuid.UUID,
    body: UpdateCategoryRequest,
    claims: AuthDep,
    db: DbDep,
    service: CategoryServiceDep,
) -> CategoryResponse:
    """Partially update the category with the given id."""
    result = _to_category(
        service.update(
            claims.actor_id(), category_id, body.model_dump(exclude_unset=True)
        )
    )
    db.commit()
    return result


@category_router.delete(f"{CATEGORIES_PREFIX}/{{category_id}}", status_code=204)
def delete_category(
    category_id: uuid.UUID,
    claims: AuthDep,
    db: DbDep,
    service: CategoryServiceDep,
) -> None:
    """Delete the category with the given id."""
    service.delete(claims.actor_id(), category_id)
    db.commit()


@category_router.get(
    f"{CATEGORIES_PREFIX}/{{category_id}}/children",
    response_model=PaginatedResponse[CategoryResponse],
)
def list_category_children(
    category_id: uuid.UUID,
    service: CategoryServiceDep,
    cursor: str | None = None,
) -> PaginatedResponse[CategoryResponse]:
    """Return a paginated page of direct child categories."""
    decoded = decode_cursor(cursor) if cursor else None
    rows = service.list_by_parent(category_id, limit=PAGE_SIZE + 1, cursor=decoded)
    return paginate(
        rows=rows,
        page_size=PAGE_SIZE,
        to_response=_to_category,
        get_cursor_fields=lambda r: (r.created_at, r.id),
    )


@category_router.get(
    CATEGORIES_PREFIX,
    response_model=PaginatedResponse[CategoryResponse],
)
def list_root_categories(
    service: CategoryServiceDep,
    cursor: str | None = None,
) -> PaginatedResponse[CategoryResponse]:
    """Return a paginated page of root categories."""
    decoded = decode_cursor(cursor) if cursor else None
    rows = service.list_root(limit=PAGE_SIZE + 1, cursor=decoded)
    return paginate(
        rows=rows,
        page_size=PAGE_SIZE,
        to_response=_to_category,
        get_cursor_fields=lambda r: (r.created_at, r.id),
    )


# ---------------------------------------------------------------------------
# Brand routes
# ---------------------------------------------------------------------------

brand_router = APIRouter()


@brand_router.post(BRANDS_PREFIX, response_model=BrandResponse, status_code=201)
def create_brand(
    body: CreateBrandRequest,
    claims: AuthDep,
    db: DbDep,
    service: BrandServiceDep,
) -> BrandResponse:
    """Create a new brand."""
    result = _to_brand(service.create(actor_id=claims.actor_id(), **body.model_dump()))
    db.commit()
    return result


@brand_router.get(f"{BRANDS_PREFIX}/{{brand_id}}", response_model=BrandResponse)
def get_brand(
    brand_id: uuid.UUID,
    service: BrandServiceDep,
) -> BrandResponse:
    """Return the brand with the given id."""
    return _to_brand(service.get(brand_id))


@brand_router.patch(f"{BRANDS_PREFIX}/{{brand_id}}", response_model=BrandResponse)
def update_brand(
    brand_id: uuid.UUID,
    body: UpdateBrandRequest,
    claims: AuthDep,
    db: DbDep,
    service: BrandServiceDep,
) -> BrandResponse:
    """Partially update the brand with the given id."""
    result = _to_brand(
        service.update(claims.actor_id(), brand_id, body.model_dump(exclude_unset=True))
    )
    db.commit()
    return result


@brand_router.delete(f"{BRANDS_PREFIX}/{{brand_id}}", status_code=204)
def delete_brand(
    brand_id: uuid.UUID,
    claims: AuthDep,
    db: DbDep,
    service: BrandServiceDep,
) -> None:
    """Delete the brand with the given id."""
    service.delete(claims.actor_id(), brand_id)
    db.commit()


# ---------------------------------------------------------------------------
# Product routes
# ---------------------------------------------------------------------------

product_router = APIRouter()


@product_router.post(PRODUCTS_PREFIX, response_model=ProductResponse, status_code=201)
def create_product(
    body: CreateProductRequest,
    claims: AuthDep,
    db: DbDep,
    service: ProductServiceDep,
) -> ProductResponse:
    """Create a new product."""
    excluded = ("sku", "name", "base_price")
    result = _to_product(
        service.create(
            actor_id=claims.actor_id(),
            sku=body.sku,
            name=body.name,
            base_price=body.base_price,
            **{k: v for k, v in body.model_dump().items() if k not in excluded},
        )
    )
    db.commit()
    return result


@product_router.get(f"{PRODUCTS_PREFIX}/{{product_id}}", response_model=ProductResponse)
def get_product(
    product_id: uuid.UUID,
    service: ProductServiceDep,
) -> ProductResponse:
    """Return the product with the given id."""
    return _to_product(service.get(product_id))


@product_router.patch(
    f"{PRODUCTS_PREFIX}/{{product_id}}", response_model=ProductResponse
)
def update_product(
    product_id: uuid.UUID,
    body: UpdateProductRequest,
    claims: AuthDep,
    db: DbDep,
    service: ProductServiceDep,
) -> ProductResponse:
    """Partially update the product with the given id."""
    result = _to_product(
        service.update(
            claims.actor_id(), product_id, body.model_dump(exclude_unset=True)
        )
    )
    db.commit()
    return result


@product_router.delete(f"{PRODUCTS_PREFIX}/{{product_id}}", status_code=204)
def delete_product(
    product_id: uuid.UUID,
    claims: AuthDep,
    db: DbDep,
    service: ProductServiceDep,
) -> None:
    """Delete the product with the given id."""
    service.delete(claims.actor_id(), product_id)
    db.commit()


@product_router.get(
    f"{PRODUCTS_PREFIX}/{{product_id}}/variants",
    response_model=PaginatedResponse[VariantResponse],
)
def list_product_variants(
    product_id: uuid.UUID,
    service: VariantServiceDep,
    cursor: str | None = None,
) -> PaginatedResponse[VariantResponse]:
    """Return a paginated page of active variants for the given product."""
    decoded = decode_cursor(cursor) if cursor else None
    rows = service.list_by_product(product_id, limit=PAGE_SIZE + 1, cursor=decoded)
    return paginate(
        rows=rows,
        page_size=PAGE_SIZE,
        to_response=_to_variant,
        get_cursor_fields=lambda r: (r.created_at, r.id),
    )


@product_router.get(
    f"{BRANDS_PREFIX}/{{brand_id}}/products",
    response_model=PaginatedResponse[ProductResponse],
)
def list_brand_products(
    brand_id: uuid.UUID,
    service: ProductServiceDep,
    cursor: str | None = None,
) -> PaginatedResponse[ProductResponse]:
    """Return a paginated page of active products for the given brand."""
    decoded = decode_cursor(cursor) if cursor else None
    rows = service.list_by_brand(brand_id, limit=PAGE_SIZE + 1, cursor=decoded)
    return paginate(
        rows=rows,
        page_size=PAGE_SIZE,
        to_response=_to_product,
        get_cursor_fields=lambda r: (r.created_at, r.id),
    )


@product_router.get(
    f"{CATEGORIES_PREFIX}/{{category_id}}/products",
    response_model=PaginatedResponse[ProductResponse],
)
def list_category_products(
    category_id: uuid.UUID,
    service: ProductServiceDep,
    cursor: str | None = None,
) -> PaginatedResponse[ProductResponse]:
    """Return a paginated page of active products in the given category."""
    decoded = decode_cursor(cursor) if cursor else None
    rows = service.list_by_category(category_id, limit=PAGE_SIZE + 1, cursor=decoded)
    return paginate(
        rows=rows,
        page_size=PAGE_SIZE,
        to_response=_to_product,
        get_cursor_fields=lambda r: (r.created_at, r.id),
    )


# ---------------------------------------------------------------------------
# Variant routes
# ---------------------------------------------------------------------------

variant_router = APIRouter()


@variant_router.post(
    f"{PRODUCTS_PREFIX}/{{product_id}}/variants",
    response_model=VariantResponse,
    status_code=201,
)
def create_variant(
    request: Request,
    body: CreateVariantRequest,
    claims: AuthDep,
    db: DbDep,
    service: VariantServiceDep,
) -> VariantResponse:
    """Create a new variant for the given product."""
    product_id = VariantRequestContext.model_validate(
        {"request": request}
    ).path_params.product_id
    result = _to_variant(
        service.create(
            actor_id=claims.actor_id(),
            product_id=product_id,
            sku=body.sku,
            price=body.price,
            attributes=body.attributes,
        )
    )
    db.commit()
    return result


@variant_router.get(
    f"{PRODUCTS_PREFIX}/{{product_id}}/variants/{{variant_id}}",
    response_model=VariantResponse,
)
def get_variant(
    variant_id: uuid.UUID,
    service: VariantServiceDep,
) -> VariantResponse:
    """Return the variant with the given id."""
    return _to_variant(service.get(variant_id))


@variant_router.patch(
    f"{PRODUCTS_PREFIX}/{{product_id}}/variants/{{variant_id}}",
    response_model=VariantResponse,
)
def update_variant(
    variant_id: uuid.UUID,
    body: UpdateVariantRequest,
    claims: AuthDep,
    db: DbDep,
    service: VariantServiceDep,
) -> VariantResponse:
    """Partially update the variant with the given id."""
    result = _to_variant(
        service.update(
            claims.actor_id(), variant_id, body.model_dump(exclude_unset=True)
        )
    )
    db.commit()
    return result


@variant_router.delete(
    f"{PRODUCTS_PREFIX}/{{product_id}}/variants/{{variant_id}}", status_code=204
)
def delete_variant(
    variant_id: uuid.UUID,
    claims: AuthDep,
    db: DbDep,
    service: VariantServiceDep,
) -> None:
    """Delete the variant with the given id."""
    service.delete(claims.actor_id(), variant_id)
    db.commit()


# ---------------------------------------------------------------------------
# CategoryAttribute routes
# ---------------------------------------------------------------------------

attribute_router = APIRouter()


@attribute_router.post(
    f"{CATEGORIES_PREFIX}/{{category_id}}/attributes",
    response_model=CategoryAttributeResponse,
    status_code=201,
)
def create_attribute(
    request: Request,
    body: CreateCategoryAttributeRequest,
    claims: AuthDep,
    db: DbDep,
    service: AttributeServiceDep,
) -> CategoryAttributeResponse:
    """Create a new attribute definition for the given category."""
    category_id = AttributeRequestContext.model_validate(
        {"request": request}
    ).path_params.category_id
    result = _to_attribute(
        service.create(
            actor_id=claims.actor_id(),
            category_id=category_id,
            key=body.key,
            value_type=body.value_type,
            required=body.required,
        )
    )
    db.commit()
    return result


@attribute_router.get(
    f"{CATEGORIES_PREFIX}/{{category_id}}/attributes/{{attribute_id}}",
    response_model=CategoryAttributeResponse,
)
def get_attribute(
    attribute_id: uuid.UUID,
    service: AttributeServiceDep,
) -> CategoryAttributeResponse:
    """Return the attribute with the given id."""
    return _to_attribute(service.get(attribute_id))


@attribute_router.patch(
    f"{CATEGORIES_PREFIX}/{{category_id}}/attributes/{{attribute_id}}",
    response_model=CategoryAttributeResponse,
)
def update_attribute(
    attribute_id: uuid.UUID,
    body: UpdateCategoryAttributeRequest,
    claims: AuthDep,
    db: DbDep,
    service: AttributeServiceDep,
) -> CategoryAttributeResponse:
    """Partially update the attribute with the given id."""
    result = _to_attribute(
        service.update(
            claims.actor_id(), attribute_id, body.model_dump(exclude_unset=True)
        )
    )
    db.commit()
    return result


@attribute_router.delete(
    f"{CATEGORIES_PREFIX}/{{category_id}}/attributes/{{attribute_id}}", status_code=204
)
def delete_attribute(
    attribute_id: uuid.UUID,
    claims: AuthDep,
    db: DbDep,
    service: AttributeServiceDep,
) -> None:
    """Delete the attribute with the given id."""
    service.delete(claims.actor_id(), attribute_id)
    db.commit()


@attribute_router.get(
    f"{CATEGORIES_PREFIX}/{{category_id}}/attributes",
    response_model=PaginatedResponse[CategoryAttributeResponse],
)
def list_category_attributes(
    category_id: uuid.UUID,
    service: AttributeServiceDep,
    cursor: str | None = None,
) -> PaginatedResponse[CategoryAttributeResponse]:
    """Return a paginated page of attribute definitions for the given category."""
    decoded = decode_cursor(cursor) if cursor else None
    rows = service.list_by_category(category_id, limit=PAGE_SIZE + 1, cursor=decoded)
    return paginate(
        rows=rows,
        page_size=PAGE_SIZE,
        to_response=_to_attribute,
        get_cursor_fields=lambda r: (r.created_at, r.id),
    )


# ---------------------------------------------------------------------------
# Exception handlers
# ---------------------------------------------------------------------------


def register_exception_handlers(app: FastAPI) -> None:
    """Register catalog domain exception handlers on the FastAPI app.

    Args:
        app: The FastAPI application instance.
    """

    @app.exception_handler(CatalogError)
    def handle_catalog_error(request: Request, exc: CatalogError) -> JSONResponse:
        logger.warning("catalog_error code=%s message=%s", exc.code, str(exc))
        return JSONResponse(
            status_code=getattr(exc, "status_code", 400),
            content=error_response(exc.code, str(exc)),
        )
