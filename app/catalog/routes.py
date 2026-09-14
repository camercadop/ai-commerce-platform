import logging
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.catalog.exceptions import (
    BrandAlreadyExists,
    BrandNotFound,
    CategoryAlreadyExists,
    CategoryAttributeAlreadyExists,
    CategoryAttributeNotFound,
    CategoryNotFound,
    InvalidVariantAttributes,
    ProductAlreadyExists,
    ProductNotFound,
    VariantAlreadyExists,
    VariantNotFound,
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
    CRUDRouter,
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

    Never called directly. app.py replaces this with a MongoAuditRepository
    instance built from MongoSettings.
    """
    raise NotImplementedError  # pragma: no cover


def _broker_dependency() -> MessageBroker:
    """Sentinel dependency overridden at application startup via dependency_overrides.

    Never called directly. app.py replaces this with a concrete MessageBroker
    implementation built from broker settings.
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
# Category router
# ---------------------------------------------------------------------------


def build_category_router(audit: AuditPort, broker: MessageBroker) -> APIRouter:
    """Build the category CRUD router.

    Args:
        audit: The audit port to inject into service instances.
        broker: The message broker port to inject into service instances.
    """
    return CRUDRouter(
        prefix=CATEGORIES_PREFIX,
        response_model=CategoryResponse,
        to_response=_to_category,
        create_schema=CreateCategoryRequest,
        update_schema=UpdateCategoryRequest,
        get_db_dep=_db_dependency,
        create_fn=lambda body, db, context: CategoryService(db, audit, broker).create(
            actor_id=uuid.UUID(int=0),
            name=body.name,
            description=body.description,
            parent_id=body.parent_id,
        ),
        get_fn=lambda resource_id, db, context: CategoryService(db, audit, broker).get(
            resource_id
        ),
        update_fn=lambda resource_id, data, db, context: CategoryService(
            db, audit, broker
        ).update(uuid.UUID(int=0), resource_id, data),
        delete_fn=lambda resource_id, db, context: CategoryService(
            db, audit, broker
        ).delete(uuid.UUID(int=0), resource_id),
    )


category_sub_router = APIRouter()


@category_sub_router.get(
    f"{CATEGORIES_PREFIX}/{{category_id}}/children",
    response_model=PaginatedResponse[CategoryResponse],
)
def list_category_children(
    category_id: uuid.UUID,
    db: DbDep,
    audit: AuditDep,
    broker: BrokerDep,
    cursor: str | None = None,
) -> PaginatedResponse[CategoryResponse]:
    """Return a paginated page of direct child categories."""
    decoded = decode_cursor(cursor) if cursor else None
    rows = CategoryService(db, audit, broker).list_by_parent(
        category_id, limit=PAGE_SIZE + 1, cursor=decoded
    )
    return paginate(
        rows=rows,
        page_size=PAGE_SIZE,
        to_response=_to_category,
        get_cursor_fields=lambda r: (r.created_at, r.id),
    )


@category_sub_router.get(
    CATEGORIES_PREFIX,
    response_model=PaginatedResponse[CategoryResponse],
)
def list_root_categories(
    db: DbDep,
    audit: AuditDep,
    broker: BrokerDep,
    cursor: str | None = None,
) -> PaginatedResponse[CategoryResponse]:
    """Return a paginated page of root categories."""
    decoded = decode_cursor(cursor) if cursor else None
    rows = CategoryService(db, audit, broker).list_root(
        limit=PAGE_SIZE + 1, cursor=decoded
    )
    return paginate(
        rows=rows,
        page_size=PAGE_SIZE,
        to_response=_to_category,
        get_cursor_fields=lambda r: (r.created_at, r.id),
    )


# ---------------------------------------------------------------------------
# Brand router
# ---------------------------------------------------------------------------


def build_brand_router(audit: AuditPort, broker: MessageBroker) -> APIRouter:
    """Build the brand CRUD router.

    Args:
        audit: The audit port to inject into service instances.
        broker: The message broker port to inject into service instances.
    """
    return CRUDRouter(
        prefix=BRANDS_PREFIX,
        response_model=BrandResponse,
        to_response=_to_brand,
        create_schema=CreateBrandRequest,
        update_schema=UpdateBrandRequest,
        get_db_dep=_db_dependency,
        create_fn=lambda body, db, context: BrandService(db, audit, broker).create(
            actor_id=uuid.UUID(int=0),
            **body.model_dump(),
        ),
        get_fn=lambda resource_id, db, context: BrandService(db, audit, broker).get(
            resource_id
        ),
        update_fn=lambda resource_id, data, db, context: BrandService(
            db, audit, broker
        ).update(uuid.UUID(int=0), resource_id, data),
        delete_fn=lambda resource_id, db, context: BrandService(
            db, audit, broker
        ).delete(uuid.UUID(int=0), resource_id),
    )


# ---------------------------------------------------------------------------
# Product router
# ---------------------------------------------------------------------------


def build_product_router(audit: AuditPort, broker: MessageBroker) -> APIRouter:
    """Build the product CRUD router.

    Args:
        audit: The audit port to inject into service instances.
        broker: The message broker port to inject into service instances.
    """
    return CRUDRouter(
        prefix=PRODUCTS_PREFIX,
        response_model=ProductResponse,
        to_response=_to_product,
        create_schema=CreateProductRequest,
        update_schema=UpdateProductRequest,
        get_db_dep=_db_dependency,
        create_fn=lambda body, db, context: ProductService(db, audit, broker).create(
            actor_id=uuid.UUID(int=0),
            sku=body.sku,
            name=body.name,
            base_price=body.base_price,
            **{
                k: v
                for k, v in body.model_dump().items()
                if k not in ("sku", "name", "base_price")
            },
        ),
        get_fn=lambda resource_id, db, context: ProductService(db, audit, broker).get(
            resource_id
        ),
        update_fn=lambda resource_id, data, db, context: ProductService(
            db, audit, broker
        ).update(uuid.UUID(int=0), resource_id, data),
        delete_fn=lambda resource_id, db, context: ProductService(
            db, audit, broker
        ).delete(uuid.UUID(int=0), resource_id),
    )


product_sub_router = APIRouter()


@product_sub_router.get(
    f"{PRODUCTS_PREFIX}/{{product_id}}/variants",
    response_model=PaginatedResponse[VariantResponse],
)
def list_product_variants(
    product_id: uuid.UUID,
    db: DbDep,
    audit: AuditDep,
    broker: BrokerDep,
    cursor: str | None = None,
) -> PaginatedResponse[VariantResponse]:
    """Return a paginated page of active variants for the given product."""
    decoded = decode_cursor(cursor) if cursor else None
    rows = VariantService(db, audit, broker).list_by_product(
        product_id, limit=PAGE_SIZE + 1, cursor=decoded
    )
    return paginate(
        rows=rows,
        page_size=PAGE_SIZE,
        to_response=_to_variant,
        get_cursor_fields=lambda r: (r.created_at, r.id),
    )


@product_sub_router.get(
    f"{BRANDS_PREFIX}/{{brand_id}}/products",
    response_model=PaginatedResponse[ProductResponse],
)
def list_brand_products(
    brand_id: uuid.UUID,
    db: DbDep,
    audit: AuditDep,
    broker: BrokerDep,
    cursor: str | None = None,
) -> PaginatedResponse[ProductResponse]:
    """Return a paginated page of active products for the given brand."""
    decoded = decode_cursor(cursor) if cursor else None
    rows = ProductService(db, audit, broker).list_by_brand(
        brand_id, limit=PAGE_SIZE + 1, cursor=decoded
    )
    return paginate(
        rows=rows,
        page_size=PAGE_SIZE,
        to_response=_to_product,
        get_cursor_fields=lambda r: (r.created_at, r.id),
    )


@product_sub_router.get(
    f"{CATEGORIES_PREFIX}/{{category_id}}/products",
    response_model=PaginatedResponse[ProductResponse],
)
def list_category_products(
    category_id: uuid.UUID,
    db: DbDep,
    audit: AuditDep,
    broker: BrokerDep,
    cursor: str | None = None,
) -> PaginatedResponse[ProductResponse]:
    """Return a paginated page of active products in the given category."""
    decoded = decode_cursor(cursor) if cursor else None
    rows = ProductService(db, audit, broker).list_by_category(
        category_id, limit=PAGE_SIZE + 1, cursor=decoded
    )
    return paginate(
        rows=rows,
        page_size=PAGE_SIZE,
        to_response=_to_product,
        get_cursor_fields=lambda r: (r.created_at, r.id),
    )


# ---------------------------------------------------------------------------
# Variant router
# ---------------------------------------------------------------------------


def build_variant_router(audit: AuditPort, broker: MessageBroker) -> APIRouter:
    """Build the variant CRUD router nested under products.

    The POST route lives at /products/{product_id}/variants. The product_id
    path param is extracted from context['request'] and coerced via
    VariantRequestContext.

    Args:
        audit: The audit port to inject into service instances.
        broker: The message broker port to inject into service instances.
    """
    return CRUDRouter(
        prefix=f"{PRODUCTS_PREFIX}/{{product_id}}/variants",
        response_model=VariantResponse,
        to_response=_to_variant,
        create_schema=CreateVariantRequest,
        update_schema=UpdateVariantRequest,
        get_db_dep=_db_dependency,
        create_fn=lambda body, db, context: VariantService(db, audit, broker).create(
            actor_id=uuid.UUID(int=0),
            product_id=VariantRequestContext.model_validate(
                {"request": context["request"]}
            ).path_params.product_id,
            sku=body.sku,
            price=body.price,
            attributes=body.attributes,
        ),
        get_fn=lambda resource_id, db, context: VariantService(db, audit, broker).get(
            resource_id
        ),
        update_fn=lambda resource_id, data, db, context: VariantService(
            db, audit, broker
        ).update(uuid.UUID(int=0), resource_id, data),
        delete_fn=lambda resource_id, db, context: VariantService(
            db, audit, broker
        ).delete(uuid.UUID(int=0), resource_id),
    )


# ---------------------------------------------------------------------------
# CategoryAttribute router
# ---------------------------------------------------------------------------


def build_attribute_router(audit: AuditPort, broker: MessageBroker) -> APIRouter:
    """Build the category attribute CRUD router nested under categories.

    The POST route lives at /categories/{category_id}/attributes. The
    category_id path param is extracted from context['request'] and coerced
    via AttributeRequestContext.

    Args:
        audit: The audit port to inject into service instances.
        broker: The message broker port to inject into service instances.
    """
    return CRUDRouter(
        prefix=f"{CATEGORIES_PREFIX}/{{category_id}}/attributes",
        response_model=CategoryAttributeResponse,
        to_response=_to_attribute,
        create_schema=CreateCategoryAttributeRequest,
        update_schema=UpdateCategoryAttributeRequest,
        get_db_dep=_db_dependency,
        create_fn=lambda body, db, context: CategoryAttributeService(
            db, audit, broker
        ).create(
            actor_id=uuid.UUID(int=0),
            category_id=AttributeRequestContext.model_validate(
                {"request": context["request"]}
            ).path_params.category_id,
            key=body.key,
            value_type=body.value_type,
            required=body.required,
        ),
        get_fn=lambda resource_id, db, context: CategoryAttributeService(
            db, audit, broker
        ).get(resource_id),
        update_fn=lambda resource_id, data, db, context: CategoryAttributeService(
            db, audit, broker
        ).update(uuid.UUID(int=0), resource_id, data),
        delete_fn=lambda resource_id, db, context: CategoryAttributeService(
            db, audit, broker
        ).delete(uuid.UUID(int=0), resource_id),
    )


attribute_sub_router = APIRouter()


@attribute_sub_router.get(
    f"{CATEGORIES_PREFIX}/{{category_id}}/attributes",
    response_model=PaginatedResponse[CategoryAttributeResponse],
)
def list_category_attributes(
    category_id: uuid.UUID,
    db: DbDep,
    audit: AuditDep,
    broker: BrokerDep,
    cursor: str | None = None,
) -> PaginatedResponse[CategoryAttributeResponse]:
    """Return a paginated page of attribute definitions for the given category."""
    decoded = decode_cursor(cursor) if cursor else None
    rows = CategoryAttributeService(db, audit, broker).list_by_category(
        category_id, limit=PAGE_SIZE + 1, cursor=decoded
    )
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

    Maps domain exceptions to HTTP responses using the platform error envelope.
    Add new handlers here as new domain exceptions are introduced.

    Args:
        app: The FastAPI application instance.
    """

    @app.exception_handler(CategoryNotFound)
    def handle_category_not_found(
        request: Request, exc: CategoryNotFound
    ) -> JSONResponse:
        logger.warning("Category not found: %s", exc.resource_id)
        return JSONResponse(status_code=404, content=error_response(exc.code, str(exc)))

    @app.exception_handler(CategoryAlreadyExists)
    def handle_category_already_exists(
        request: Request, exc: CategoryAlreadyExists
    ) -> JSONResponse:
        logger.warning("Category already exists: %s", exc.identifier)
        return JSONResponse(status_code=409, content=error_response(exc.code, str(exc)))

    @app.exception_handler(BrandNotFound)
    def handle_brand_not_found(request: Request, exc: BrandNotFound) -> JSONResponse:
        logger.warning("Brand not found: %s", exc.resource_id)
        return JSONResponse(status_code=404, content=error_response(exc.code, str(exc)))

    @app.exception_handler(BrandAlreadyExists)
    def handle_brand_already_exists(
        request: Request, exc: BrandAlreadyExists
    ) -> JSONResponse:
        logger.warning("Brand already exists: %s", exc.identifier)
        return JSONResponse(status_code=409, content=error_response(exc.code, str(exc)))

    @app.exception_handler(ProductNotFound)
    def handle_product_not_found(
        request: Request, exc: ProductNotFound
    ) -> JSONResponse:
        logger.warning("Product not found: %s", exc.resource_id)
        return JSONResponse(status_code=404, content=error_response(exc.code, str(exc)))

    @app.exception_handler(ProductAlreadyExists)
    def handle_product_already_exists(
        request: Request, exc: ProductAlreadyExists
    ) -> JSONResponse:
        logger.warning("Product already exists: %s", exc.identifier)
        return JSONResponse(status_code=409, content=error_response(exc.code, str(exc)))

    @app.exception_handler(VariantNotFound)
    def handle_variant_not_found(
        request: Request, exc: VariantNotFound
    ) -> JSONResponse:
        logger.warning("Variant not found: %s", exc.resource_id)
        return JSONResponse(status_code=404, content=error_response(exc.code, str(exc)))

    @app.exception_handler(VariantAlreadyExists)
    def handle_variant_already_exists(
        request: Request, exc: VariantAlreadyExists
    ) -> JSONResponse:
        logger.warning("Variant already exists: %s", exc.identifier)
        return JSONResponse(status_code=409, content=error_response(exc.code, str(exc)))

    @app.exception_handler(CategoryAttributeNotFound)
    def handle_attribute_not_found(
        request: Request, exc: CategoryAttributeNotFound
    ) -> JSONResponse:
        logger.warning("CategoryAttribute not found: %s", exc.resource_id)
        return JSONResponse(status_code=404, content=error_response(exc.code, str(exc)))

    @app.exception_handler(CategoryAttributeAlreadyExists)
    def handle_attribute_already_exists(
        request: Request, exc: CategoryAttributeAlreadyExists
    ) -> JSONResponse:
        logger.warning("CategoryAttribute already exists: %s", exc.identifier)
        return JSONResponse(status_code=409, content=error_response(exc.code, str(exc)))

    @app.exception_handler(InvalidVariantAttributes)
    def handle_invalid_variant_attributes(
        request: Request, exc: InvalidVariantAttributes
    ) -> JSONResponse:
        logger.warning("Invalid variant attributes: %s", exc.violations)
        return JSONResponse(status_code=400, content=error_response(exc.code, str(exc)))
