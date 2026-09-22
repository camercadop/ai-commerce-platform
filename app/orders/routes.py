import logging
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.orders.exceptions import OrderError, OrderNotFound
from app.orders.models import Order
from app.orders.ports import AdjustmentRulesPort, CartPort
from app.orders.repository import OrderItemRepository, OrderRepository
from app.orders.schemas import OrderResponse, PlaceOrderRequest
from app.orders.service import OrderService
from app.shared.api import error_response
from app.shared.audit_log import AuditPort
from app.shared.auth import TokenClaims
from app.shared.events import MessageBroker

logger = logging.getLogger(__name__)

PREFIX = "/api/v1/orders"


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


def _cart_dependency() -> CartPort:
    """Sentinel dependency overridden at application startup via dependency_overrides.

    Never called directly. app.py replaces this with a concrete CartPort
    implementation.
    """
    raise NotImplementedError  # pragma: no cover


def _adjustment_rules_dependency() -> AdjustmentRulesPort:
    """Sentinel dependency overridden at application startup via dependency_overrides.

    Never called directly. app.py replaces this with a concrete AdjustmentRulesPort
    implementation.
    """
    raise NotImplementedError  # pragma: no cover


DbDep = Annotated[Session, Depends(_db_dependency)]
AuthDep = Annotated[TokenClaims, Depends(_auth_dependency)]
AuditDep = Annotated[AuditPort, Depends(_audit_dependency)]
BrokerDep = Annotated[MessageBroker, Depends(_broker_dependency)]
CartDep = Annotated[CartPort, Depends(_cart_dependency)]
AdjustmentRulesDep = Annotated[
    AdjustmentRulesPort, Depends(_adjustment_rules_dependency)
]


def _to_order(obj: Order) -> OrderResponse:
    """Map an Order model instance to an OrderResponse schema."""
    return OrderResponse.model_validate(obj, from_attributes=True)


router = APIRouter()


@router.post(PREFIX, response_model=OrderResponse, status_code=201)
def place_order(
    body: PlaceOrderRequest,
    db: DbDep,
    auth: AuthDep,
    audit: AuditDep,
    broker: BrokerDep,
    cart: CartDep,
    adjustment_rules: AdjustmentRulesDep,
) -> OrderResponse:
    """Place an order from an active cart checkout."""
    service = OrderService(
        OrderRepository(db),
        OrderItemRepository(db),
        cart,
        audit,
        broker,
        adjustment_rules,
    )
    order = service.place_order(
        cart_id=body.cart_id,
        actor_id=auth.actor_id(),
    )
    db.commit()
    return _to_order(order)


@router.get(f"{PREFIX}/{{order_id}}", response_model=OrderResponse)
def get_order(
    order_id: uuid.UUID,
    db: DbDep,
    auth: AuthDep,
    audit: AuditDep,
    broker: BrokerDep,
    cart: CartDep,
    adjustment_rules: AdjustmentRulesDep,
) -> OrderResponse:
    """Return an order with its items and adjustments."""
    service = OrderService(
        OrderRepository(db),
        OrderItemRepository(db),
        cart,
        audit,
        broker,
        adjustment_rules,
    )
    return _to_order(service.get_order(order_id))


# ---------------------------------------------------------------------------
# Exception handlers
# ---------------------------------------------------------------------------


def register_exception_handlers(app: FastAPI) -> None:
    """Register orders domain exception handlers on the FastAPI app.

    Args:
        app: The FastAPI application instance.
    """

    @app.exception_handler(OrderNotFound)
    def handle_order_not_found(request: Request, exc: OrderNotFound) -> JSONResponse:
        logger.warning("order_not_found id=%s", exc.resource_id)
        return JSONResponse(status_code=404, content=error_response(exc.code, str(exc)))

    @app.exception_handler(OrderError)
    def handle_order_error(request: Request, exc: OrderError) -> JSONResponse:
        logger.warning("order_error code=%s message=%s", exc.code, str(exc))
        return JSONResponse(
            status_code=exc.status_code, content=error_response(exc.code, str(exc))
        )
