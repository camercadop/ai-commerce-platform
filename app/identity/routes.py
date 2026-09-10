import logging
import uuid
from collections.abc import Callable
from typing import Annotated

from fastapi import APIRouter, Depends, FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.identity.exceptions import (
    AddressNotFound,
    CustomerAlreadyExists,
    CustomerNotFound,
    InvalidPreferenceKey,
)
from app.identity.schemas import (
    AddAddressRequest,
    AddressResponse,
    CustomerResponse,
    RegisterCustomerRequest,
    UpdateAddressRequest,
    UpdateProfileRequest,
    UpsertPreferencesRequest,
)
from app.identity.service import ADDRESS_PAGE_SIZE, AddressService, CustomerService
from app.shared.api import CRUDRouter, decode_cursor, error_response, paginate
from app.shared.api.schemas import PaginatedResponse
from app.shared.audit_log import AuditPort
from app.shared.auth import TokenClaims

logger = logging.getLogger(__name__)

PREFIX = "/api/v1/customers"


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


DbDep = Annotated[Session, Depends(_db_dependency)]
AuthDep = Annotated[TokenClaims, Depends(_auth_dependency)]
AuditDep = Annotated[AuditPort, Depends(_audit_dependency)]


def _to_customer_response(customer: object) -> CustomerResponse:
    return CustomerResponse.model_validate(customer, from_attributes=True)


def _to_address_response(address: object) -> AddressResponse:
    return AddressResponse.model_validate(address, from_attributes=True)


def _require_owner(
    customer_id: uuid.UUID,
    claims: AuthDep,
    db: DbDep,
    audit: AuditDep,
) -> None:
    """Raise 404 if the authenticated user does not own the given customer profile.

    Ownership is determined by matching the JWT subject claim against the
    customer's identity_provider_id. Returns 404 (not 403) to avoid leaking
    resource existence to unauthorized callers.

    Args:
        customer_id: The UUID of the customer being accessed.
        claims: Decoded JWT claims from the Authorization header.
        db: Active database session.
        audit: Audit port for recording state-changing operations.
    """
    service = CustomerService(db, audit)
    customer = service.repo.get_by_id(customer_id)
    if customer is None or customer.identity_provider_id != claims.sub:
        raise CustomerNotFound(customer_id)


def _create_customer(audit: AuditPort) -> Callable[..., object]:
    def _fn(body: RegisterCustomerRequest, db: Session) -> object:
        return CustomerService(db, audit=audit).register(
            identity_provider_id=body.identity_provider_id,
            email=body.email,
            first_name=body.first_name,
            last_name=body.last_name,
        )

    return _fn


def _get_customer(audit: AuditPort) -> Callable[..., object]:
    def _fn(customer_id: uuid.UUID, db: Session) -> object:
        return CustomerService(db, audit=audit).get_profile(customer_id)

    return _fn


def _update_customer(audit: AuditPort) -> Callable[..., object]:
    def _fn(customer_id: uuid.UUID, data: dict[str, object], db: Session) -> object:
        return CustomerService(db, audit=audit).update_profile(customer_id, data)

    return _fn


def _delete_customer(audit: AuditPort) -> Callable[..., None]:
    def _fn(customer_id: uuid.UUID, db: Session) -> None:
        service = CustomerService(db, audit=audit)
        customer = service.get_profile(customer_id)
        service.repo.delete(customer)

    return _fn


def build_customer_router(audit: AuditPort) -> APIRouter:
    """Build the customer CRUD router with the given audit port.

    Closes over the audit instance so CRUDRouter callbacks do not need to
    call the _audit_dependency sentinel directly.

    Args:
        audit: The audit port to inject into service instances.
    """
    return CRUDRouter(
        prefix=PREFIX,
        response_model=CustomerResponse,
        to_response=_to_customer_response,
        create_schema=RegisterCustomerRequest,
        update_schema=UpdateProfileRequest,
        get_db_dep=_db_dependency,
        create_fn=_create_customer(audit),
        get_fn=_get_customer(audit),
        update_fn=_update_customer(audit),
        delete_fn=_delete_customer(audit),
    )


address_router = APIRouter(prefix=PREFIX, dependencies=[Depends(_require_owner)])


@address_router.patch("/{customer_id}/preferences", status_code=200)
def upsert_preferences(
    customer_id: uuid.UUID,
    body: UpsertPreferencesRequest,
    db: DbDep,
    audit: AuditDep,
) -> dict[str, str]:
    """Upsert preferences for the given customer."""
    CustomerService(db, audit).update_preferences(customer_id, body.preferences)
    db.commit()
    return {}


@address_router.get(
    "/{customer_id}/addresses",
    response_model=PaginatedResponse[AddressResponse],
)
def list_addresses(
    customer_id: uuid.UUID,
    db: DbDep,
    audit: AuditDep,
    cursor: str | None = None,
) -> PaginatedResponse[AddressResponse]:
    """Return a paginated page of active addresses for the given customer."""
    decoded_cursor = decode_cursor(cursor) if cursor else None
    rows = AddressService(db, audit).list_addresses(customer_id, decoded_cursor)
    return paginate(
        rows=rows,
        page_size=ADDRESS_PAGE_SIZE,
        to_response=_to_address_response,
        get_cursor_fields=lambda a: (a.created_at, a.id),
    )


@address_router.post(
    "/{customer_id}/addresses",
    response_model=AddressResponse,
    status_code=201,
)
def add_address(
    customer_id: uuid.UUID,
    body: AddAddressRequest,
    db: DbDep,
    audit: AuditDep,
) -> AddressResponse:
    """Add a new address for the given customer."""
    address = AddressService(db, audit).add_address(customer_id, **body.model_dump())
    db.commit()
    return _to_address_response(address)


@address_router.patch(
    "/{customer_id}/addresses/{address_id}", response_model=AddressResponse
)
def update_address(
    customer_id: uuid.UUID,
    address_id: uuid.UUID,
    body: UpdateAddressRequest,
    db: DbDep,
    audit: AuditDep,
) -> AddressResponse:
    """Partially update an address owned by the given customer."""
    address = AddressService(db, audit).update_address(
        customer_id, address_id, body.model_dump(exclude_unset=True)
    )
    db.commit()
    return _to_address_response(address)


@address_router.delete("/{customer_id}/addresses/{address_id}", status_code=204)
def remove_address(
    customer_id: uuid.UUID,
    address_id: uuid.UUID,
    db: DbDep,
    audit: AuditDep,
) -> None:
    """Soft-delete an address owned by the given customer."""
    AddressService(db, audit).remove_address(customer_id, address_id)
    db.commit()


def register_exception_handlers(app: FastAPI) -> None:
    """Register identity domain exception handlers on the FastAPI app.

    Maps domain exceptions to HTTP responses using the platform error envelope.
    Add new handlers here as new domain exceptions are introduced.

    Args:
        app: The FastAPI application instance.
    """

    @app.exception_handler(CustomerNotFound)
    def handle_customer_not_found(
        request: Request, exc: CustomerNotFound
    ) -> JSONResponse:
        logger.warning("Customer not found: %s", exc.resource_id)
        return JSONResponse(
            status_code=404,
            content=error_response(exc.code, str(exc)),
        )

    @app.exception_handler(CustomerAlreadyExists)
    def handle_customer_already_exists(
        request: Request, exc: CustomerAlreadyExists
    ) -> JSONResponse:
        logger.warning("Customer already exists: %s", exc.identifier)
        return JSONResponse(
            status_code=409,
            content=error_response(exc.code, str(exc)),
        )

    @app.exception_handler(AddressNotFound)
    def handle_address_not_found(
        request: Request, exc: AddressNotFound
    ) -> JSONResponse:
        logger.warning("Address not found: %s", exc.resource_id)
        return JSONResponse(
            status_code=404,
            content=error_response(exc.code, str(exc)),
        )

    @app.exception_handler(InvalidPreferenceKey)
    def handle_invalid_preference_key(
        request: Request, exc: InvalidPreferenceKey
    ) -> JSONResponse:
        logger.warning("Invalid preference keys: %s", exc.disallowed_keys)
        return JSONResponse(
            status_code=400,
            content=error_response(exc.code, str(exc)),
        )
