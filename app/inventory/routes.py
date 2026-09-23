import logging
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.inventory.exceptions import InventoryError
from app.inventory.repository import InventoryRepository, ReservationRepository
from app.inventory.schemas import (
    AdjustStockRequest,
    CreateInventoryItemRequest,
    InventoryItemResponse,
    ReservationResponse,
    ReserveStockRequest,
)
from app.inventory.service import InventoryService
from app.shared.api import error_response
from app.shared.audit_log.port import AuditPort
from app.shared.auth import TokenClaims
from app.shared.events import MessageBroker

logger = logging.getLogger(__name__)

PREFIX = "/api/v1/inventory"
router = APIRouter()


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


@router.post(PREFIX + "/items", response_model=InventoryItemResponse, status_code=201)
def create_inventory_item(
    body: CreateInventoryItemRequest,
    db: DbDep,
    auth: AuthDep,
    audit: AuditDep,
    broker: BrokerDep,
) -> InventoryItemResponse:
    """Create a new inventory item with initial stock quantity."""
    service = InventoryService(
        InventoryRepository(db),
        ReservationRepository(db),
        audit,
        broker,
    )
    item = service.create_inventory_item(
        variant_id=body.variant_id,
        initial_quantity=body.initial_quantity,
        actor_id=auth.actor_id(),
    )
    db.commit()
    return InventoryItemResponse.model_validate(item, from_attributes=True)


@router.get(PREFIX + "/items/{variant_id}", response_model=InventoryItemResponse)
def get_inventory(
    variant_id: uuid.UUID,
    db: DbDep,
    auth: AuthDep,
    audit: AuditDep,
    broker: BrokerDep,
) -> InventoryItemResponse:
    """Return the inventory item with its current stock levels."""
    service = InventoryService(
        InventoryRepository(db),
        ReservationRepository(db),
        audit,
        broker,
    )
    item = service.get_inventory(variant_id)
    return InventoryItemResponse.model_validate(item, from_attributes=True)


@router.post(
    PREFIX + "/items/{variant_id}/adjust", response_model=InventoryItemResponse
)
def adjust_stock(
    variant_id: uuid.UUID,
    body: AdjustStockRequest,
    db: DbDep,
    auth: AuthDep,
    audit: AuditDep,
    broker: BrokerDep,
) -> InventoryItemResponse:
    """Adjust stock quantity by the given delta."""
    service = InventoryService(
        InventoryRepository(db),
        ReservationRepository(db),
        audit,
        broker,
    )
    item = service.adjust_stock(
        variant_id=variant_id,
        delta=body.delta,
        note=body.note,
        actor_id=auth.actor_id(),
    )
    db.commit()
    return InventoryItemResponse.model_validate(item, from_attributes=True)


@router.post(
    PREFIX + "/reservations", response_model=ReservationResponse, status_code=201
)
def reserve_stock(
    body: ReserveStockRequest,
    db: DbDep,
    auth: AuthDep,
    audit: AuditDep,
    broker: BrokerDep,
) -> ReservationResponse:
    """Reserve stock for an order."""
    service = InventoryService(
        InventoryRepository(db),
        ReservationRepository(db),
        audit,
        broker,
    )
    reservation = service.reserve(
        variant_id=body.variant_id,
        order_id=body.order_id,
        quantity=body.quantity,
        actor_id=auth.actor_id(),
    )
    db.commit()
    return ReservationResponse.model_validate(reservation, from_attributes=True)


@router.post(
    PREFIX + "/reservations/{reservation_id}/release",
    response_model=ReservationResponse,
)
def release_reservation(
    reservation_id: uuid.UUID,
    db: DbDep,
    auth: AuthDep,
    audit: AuditDep,
    broker: BrokerDep,
) -> ReservationResponse:
    """Release a stock reservation."""
    service = InventoryService(
        InventoryRepository(db),
        ReservationRepository(db),
        audit,
        broker,
    )
    reservation = service.release_reservation(
        reservation_id=reservation_id,
        actor_id=auth.actor_id(),
    )
    db.commit()
    return ReservationResponse.model_validate(reservation, from_attributes=True)


@router.post(
    PREFIX + "/reservations/{reservation_id}/confirm",
    response_model=ReservationResponse,
)
def confirm_reservation(
    reservation_id: uuid.UUID,
    db: DbDep,
    auth: AuthDep,
    audit: AuditDep,
    broker: BrokerDep,
) -> ReservationResponse:
    """Confirm a stock reservation (payment success)."""
    service = InventoryService(
        InventoryRepository(db),
        ReservationRepository(db),
        audit,
        broker,
    )
    reservation = service.confirm_reservation(
        reservation_id=reservation_id,
        actor_id=auth.actor_id(),
    )
    db.commit()
    return ReservationResponse.model_validate(reservation, from_attributes=True)


# ---------------------------------------------------------------------------
# Exception handlers
# ---------------------------------------------------------------------------


def register_exception_handlers(app: FastAPI) -> None:
    """Register inventory domain exception handlers on the FastAPI app.

    Args:
        app: The FastAPI application instance.
    """

    @app.exception_handler(InventoryError)
    def handle_inventory_error(request: Request, exc: InventoryError) -> JSONResponse:
        logger.warning("inventory_error code=%s message=%s", exc.code, str(exc))
        return JSONResponse(
            status_code=getattr(exc, "status_code", 400),
            content=error_response(exc.code, str(exc)),
        )
