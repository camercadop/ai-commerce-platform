import logging
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.identity.exceptions import (
    AddressNotFound,
    CustomerAlreadyExists,
    CustomerNotFound,
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
from app.identity.service import AddressService, CustomerService
from app.shared.api import CRUDRouter, error_response
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


DbDep = Annotated[Session, Depends(_db_dependency)]
AuthDep = Annotated[TokenClaims, Depends(_auth_dependency)]


def _to_customer_response(customer: object) -> CustomerResponse:
    return CustomerResponse.model_validate(customer, from_attributes=True)


def _to_address_response(address: object) -> AddressResponse:
    return AddressResponse.model_validate(address, from_attributes=True)


def _require_owner(
    customer_id: uuid.UUID,
    claims: AuthDep,
    db: DbDep,
) -> None:
    """Raise 404 if the authenticated user does not own the given customer profile.

    Ownership is determined by matching the JWT subject claim against the
    customer's identity_provider_id. Returns 404 (not 403) to avoid leaking
    resource existence to unauthorized callers.

    Args:
        customer_id: The UUID of the customer being accessed.
        claims: Decoded JWT claims from the Authorization header.
        db: Active database session.
    """
    service = CustomerService(db)
    customer = service.repo.get_by_id(customer_id)
    if customer is None or customer.identity_provider_id != claims.sub:
        raise CustomerNotFound(customer_id)


def _create_customer(body: RegisterCustomerRequest, db: Session) -> object:
    return CustomerService(db).register(
        identity_provider_id=body.identity_provider_id,
        email=body.email,
        first_name=body.first_name,
        last_name=body.last_name,
    )


def _get_customer(customer_id: uuid.UUID, db: Session) -> object:
    return CustomerService(db).get_profile(customer_id)


def _update_customer(
    customer_id: uuid.UUID, data: dict[str, object], db: Session
) -> object:
    return CustomerService(db).update_profile(customer_id, data)


def _delete_customer(customer_id: uuid.UUID, db: Session) -> None:
    service = CustomerService(db)
    customer = service.get_profile(customer_id)
    service.repo.delete(customer)


customer_router = CRUDRouter(
    prefix=PREFIX,
    response_model=CustomerResponse,
    to_response=_to_customer_response,
    create_schema=RegisterCustomerRequest,
    update_schema=UpdateProfileRequest,
    get_db_dep=_db_dependency,
    create_fn=_create_customer,
    get_fn=_get_customer,
    update_fn=_update_customer,
    delete_fn=_delete_customer,
)

address_router = APIRouter(prefix=PREFIX, dependencies=[Depends(_require_owner)])


@address_router.patch("/{customer_id}/preferences", status_code=200)
def upsert_preferences(
    customer_id: uuid.UUID,
    body: UpsertPreferencesRequest,
    db: DbDep,
) -> dict[str, str]:
    """Upsert preferences for the given customer."""
    CustomerService(db).update_preferences(customer_id, body.preferences)
    db.commit()
    return {}


@address_router.get("/{customer_id}/addresses", response_model=list[AddressResponse])
def list_addresses(
    customer_id: uuid.UUID,
    db: DbDep,
) -> list[AddressResponse]:
    """Return all active addresses for the given customer."""
    addresses = AddressService(db).list_addresses(customer_id)
    return [_to_address_response(a) for a in addresses]


@address_router.post(
    "/{customer_id}/addresses",
    response_model=AddressResponse,
    status_code=201,
)
def add_address(
    customer_id: uuid.UUID,
    body: AddAddressRequest,
    db: DbDep,
) -> AddressResponse:
    """Add a new address for the given customer."""
    address = AddressService(db).add_address(customer_id, **body.model_dump())
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
) -> AddressResponse:
    """Partially update an address owned by the given customer."""
    address = AddressService(db).update_address(
        customer_id, address_id, body.model_dump(exclude_unset=True)
    )
    db.commit()
    return _to_address_response(address)


@address_router.delete("/{customer_id}/addresses/{address_id}", status_code=204)
def remove_address(
    customer_id: uuid.UUID,
    address_id: uuid.UUID,
    db: DbDep,
) -> None:
    """Soft-delete an address owned by the given customer."""
    AddressService(db).remove_address(customer_id, address_id)
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
