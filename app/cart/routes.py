import logging
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.cart.exceptions import CartError
from app.cart.models import Cart
from app.cart.ports import CatalogPort, InventoryPort
from app.cart.repository import CartItemRepository, CartRepository
from app.cart.schemas import (
    AddCartItemRequest,
    CartItemResponse,
    CartResponse,
    ClaimCartRequest,
    CreateCartRequest,
    UpdateCartItemRequest,
)
from app.cart.service import CartService
from app.shared.api import error_response
from app.shared.audit_log import AuditPort
from app.shared.auth import TokenClaims
from app.shared.events import MessageBroker

logger = logging.getLogger(__name__)

PREFIX = "/api/v1/cart"


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


def _catalog_dependency() -> CatalogPort:
    """Sentinel dependency overridden at application startup via dependency_overrides.

    Never called directly. app.py replaces this with a RepoCatalogPort when
    catalog_db_settings are provided, or a StubCatalogPort otherwise.
    """
    raise NotImplementedError  # pragma: no cover


def _inventory_dependency() -> InventoryPort:
    """Sentinel dependency overridden at application startup via dependency_overrides.

    Never called directly. app.py replaces this with a concrete InventoryPort
    when an inventory module is available, or a StubInventoryPort otherwise.
    """
    raise NotImplementedError  # pragma: no cover


DbDep = Annotated[Session, Depends(_db_dependency)]
AuthDep = Annotated[TokenClaims, Depends(_auth_dependency)]
AuditDep = Annotated[AuditPort, Depends(_audit_dependency)]
BrokerDep = Annotated[MessageBroker, Depends(_broker_dependency)]
CatalogDep = Annotated[CatalogPort, Depends(_catalog_dependency)]
InventoryDep = Annotated[InventoryPort, Depends(_inventory_dependency)]


def _to_cart(obj: Cart) -> CartResponse:
    """Map a Cart model instance to a CartResponse schema."""
    return CartResponse.model_validate(obj, from_attributes=True)


router = APIRouter()


@router.post(PREFIX, response_model=CartResponse, status_code=201)
def create_cart(
    body: CreateCartRequest,
    db: DbDep,
    auth: AuthDep,
    audit: AuditDep,
    broker: BrokerDep,
    catalog: CatalogDep,
    inventory: InventoryDep,
) -> CartResponse:
    """Create a new cart for the given session."""
    service = CartService(
        CartRepository(db),
        CartItemRepository(db),
        catalog,
        inventory,
        audit,
        broker,
    )
    cart = service.create_cart(
        session_id=body.session_id,
        customer_id=body.customer_id,
        actor_id=auth.actor_id(),
    )
    db.commit()
    return _to_cart(cart)


@router.get(f"{PREFIX}/{{cart_id}}", response_model=CartResponse)
def get_cart(
    cart_id: uuid.UUID,
    db: DbDep,
    auth: AuthDep,
    audit: AuditDep,
    broker: BrokerDep,
    catalog: CatalogDep,
    inventory: InventoryDep,
) -> CartResponse:
    """Return the cart with its items."""
    service = CartService(
        CartRepository(db),
        CartItemRepository(db),
        catalog,
        inventory,
        audit,
        broker,
    )
    return _to_cart(service.get_cart(cart_id))


@router.post(f"{PREFIX}/{{cart_id}}/claim", response_model=CartResponse)
def claim_cart(
    cart_id: uuid.UUID,
    body: ClaimCartRequest,
    db: DbDep,
    auth: AuthDep,
    audit: AuditDep,
    broker: BrokerDep,
    catalog: CatalogDep,
    inventory: InventoryDep,
) -> CartResponse:
    """Claim an anonymous cart for a customer."""
    service = CartService(
        CartRepository(db),
        CartItemRepository(db),
        catalog,
        inventory,
        audit,
        broker,
    )
    cart = service.get_cart(cart_id)
    result = service.claim_cart(
        session_id=cart.session_id,
        customer_id=body.customer_id,
        actor_id=auth.actor_id(),
    )
    db.commit()
    return _to_cart(result)


@router.post(
    f"{PREFIX}/{{cart_id}}/items", response_model=CartItemResponse, status_code=201
)
def add_cart_item(
    cart_id: uuid.UUID,
    body: AddCartItemRequest,
    db: DbDep,
    auth: AuthDep,
    audit: AuditDep,
    broker: BrokerDep,
    catalog: CatalogDep,
    inventory: InventoryDep,
) -> CartItemResponse:
    """Add an item to the cart."""
    service = CartService(
        CartRepository(db),
        CartItemRepository(db),
        catalog,
        inventory,
        audit,
        broker,
    )
    item = service.add_cart_item(
        cart_id=cart_id,
        variant_id=body.variant_id,
        quantity=body.quantity,
        actor_id=auth.actor_id(),
    )
    db.commit()
    return CartItemResponse.model_validate(item, from_attributes=True)


@router.patch(
    f"{PREFIX}/{{cart_id}}/items/{{item_id}}", response_model=CartItemResponse
)
def update_cart_item(
    cart_id: uuid.UUID,
    item_id: uuid.UUID,
    body: UpdateCartItemRequest,
    db: DbDep,
    auth: AuthDep,
    audit: AuditDep,
    broker: BrokerDep,
    catalog: CatalogDep,
    inventory: InventoryDep,
) -> CartItemResponse:
    """Update the quantity of a cart item."""
    service = CartService(
        CartRepository(db),
        CartItemRepository(db),
        catalog,
        inventory,
        audit,
        broker,
    )
    item = service.update_cart_item(
        cart_id=cart_id,
        item_id=item_id,
        quantity=body.quantity,
        actor_id=auth.actor_id(),
    )
    db.commit()
    return CartItemResponse.model_validate(item, from_attributes=True)


@router.delete(f"{PREFIX}/{{cart_id}}/items/{{item_id}}", status_code=204)
def remove_cart_item(
    cart_id: uuid.UUID,
    item_id: uuid.UUID,
    db: DbDep,
    auth: AuthDep,
    audit: AuditDep,
    broker: BrokerDep,
    catalog: CatalogDep,
    inventory: InventoryDep,
) -> None:
    """Remove an item from the cart permanently."""
    service = CartService(
        CartRepository(db),
        CartItemRepository(db),
        catalog,
        inventory,
        audit,
        broker,
    )
    service.remove_cart_item(
        cart_id=cart_id,
        item_id=item_id,
        actor_id=auth.actor_id(),
    )
    db.commit()


@router.delete(f"{PREFIX}/{{cart_id}}/clear", status_code=204)
def clear_cart(
    cart_id: uuid.UUID,
    db: DbDep,
    auth: AuthDep,
    audit: AuditDep,
    broker: BrokerDep,
    catalog: CatalogDep,
    inventory: InventoryDep,
) -> None:
    """Remove all items from the cart."""
    service = CartService(
        CartRepository(db),
        CartItemRepository(db),
        catalog,
        inventory,
        audit,
        broker,
    )
    service.clear_cart(
        cart_id=cart_id,
        actor_id=auth.actor_id(),
    )
    db.commit()


# ---------------------------------------------------------------------------
# Exception handlers
# ---------------------------------------------------------------------------


def register_exception_handlers(app: FastAPI) -> None:
    """Register cart domain exception handlers on the FastAPI app.

    Args:
        app: The FastAPI application instance.
    """

    @app.exception_handler(CartError)
    def handle_cart_error(request: Request, exc: CartError) -> JSONResponse:
        logger.warning("cart_error code=%s message=%s", exc.code, str(exc))
        return JSONResponse(
            status_code=getattr(exc, "status_code", 400),
            content=error_response(exc.code, str(exc)),
        )
