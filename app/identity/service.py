import json
import logging
import uuid
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.identity.exceptions import (
    AddressNotFound,
    CustomerAlreadyExists,
    CustomerNotFound,
    InvalidPreferenceKey,
)
from app.identity.models import CustomerPreference
from app.identity.repository import AddressRepository, CustomerRepository
from app.shared.audit_log import AuditPort, FieldChange, record_audit

logger = logging.getLogger(__name__)


ADDRESS_PAGE_SIZE = 20


@lru_cache(maxsize=1)
def _load_preferences_config() -> dict[str, Any]:
    path = Path(__file__).parent / "allowed_preferences.json"
    result: dict[str, Any] = json.loads(path.read_text())
    return result


class CustomerService:
    """Manages customer registration and profile operations.

    All write operations flush within the service but do not commit —
    the caller (route handler) owns the transaction boundary.
    """

    def __init__(self, session: Session, audit: AuditPort) -> None:
        """Initialize the service with an active database session and audit port.

        Args:
            session: The SQLAlchemy session scoped to the current request.
            audit: The audit port used to record state-changing operations.
        """
        self.repo = CustomerRepository(session)
        self.session = session
        self._audit = audit

    def register(
        self,
        identity_provider_id: str,
        email: str,
        first_name: str,
        last_name: str,
    ) -> Any:
        """Register a new customer profile.

        Raises:
            CustomerAlreadyExists: If a customer with the given identity_provider_id
                already exists.

        Args:
            identity_provider_id: JWT subject claim from the identity provider.
            email: Customer email address.
            first_name: Customer given name.
            last_name: Customer family name.
        """
        existing = self.repo.get_by_identity_provider_id(identity_provider_id)
        if existing is not None:
            logger.warning(
                "Registration attempted for existing identity_provider_id: %s",
                identity_provider_id,
            )
            raise CustomerAlreadyExists(identity_provider_id)

        try:
            customer = self.repo.create(
                identity_provider_id=identity_provider_id,
                email=email,
                first_name=first_name,
                last_name=last_name,
            )
        except IntegrityError:
            raise CustomerAlreadyExists(identity_provider_id) from None
        logger.info("Customer registered: %s", customer.id)
        return customer

    def get_profile(self, customer_id: uuid.UUID) -> Any:
        """Return the customer profile for the given id.

        Raises:
            CustomerNotFound: If no active customer with the given id exists.

        Args:
            customer_id: The UUID of the customer.
        """
        customer = self.repo.get_by_id(customer_id)
        if customer is None:
            raise CustomerNotFound(customer_id)
        return customer

    def update_profile(self, customer_id: uuid.UUID, data: dict[str, Any]) -> Any:
        """Apply a partial update to a customer profile.

        Raises:
            CustomerNotFound: If no active customer with the given id exists.

        Args:
            customer_id: The UUID of the customer to update.
            data: A dict of field names to new values.
        """
        customer = self.repo.get_by_id(customer_id)
        if customer is None:
            raise CustomerNotFound(customer_id)
        before = {k: getattr(customer, k) for k in data}
        updated = self.repo.update(customer, data)
        record_audit(
            self._audit,
            actor_id=customer_id,
            operation="update",
            action="customer.profile_updated",
            aggregate_type="customer",
            aggregate_id=customer_id,
            domain="identity",
            changes={k: FieldChange(before=before[k], after=data[k]) for k in data},
        )
        return updated

    def update_preferences(
        self, customer_id: uuid.UUID, preferences: dict[str, str]
    ) -> None:
        """Upsert a set of preferences for a customer.

        Each key in preferences is inserted if it does not exist, or updated
        if it does. Keys not present in the dict are left unchanged.

        Raises:
            CustomerNotFound: If no active customer with the given id exists.

        Args:
            customer_id: The UUID of the customer.
            preferences: A dict mapping preference keys to their new values.
        """
        customer = self.repo.get_by_id(customer_id)
        if customer is None:
            raise CustomerNotFound(customer_id)

        config = _load_preferences_config()
        unknown = preferences.keys() - config.keys()
        if unknown:
            logger.warning(
                "Unknown preference keys for customer %s: %s", customer_id, unknown
            )
            raise InvalidPreferenceKey(unknown)
        private = {k for k in preferences if config[k]["is_private"]}
        if private:
            logger.warning(
                "Attempt to set private preference keys for customer %s: %s",
                customer_id,
                private,
            )
            raise InvalidPreferenceKey(private)

        existing = {pref.key: pref for pref in customer.preferences}
        before = {k: existing[k].value if k in existing else None for k in preferences}
        for key, value in preferences.items():
            if key in existing:
                existing[key].value = value
            else:
                self.session.add(
                    CustomerPreference(
                        customer_id=customer_id,
                        key=key,
                        value=value,
                    )
                )
        self.session.flush()
        record_audit(
            self._audit,
            actor_id=customer_id,
            operation="update",
            action="customer.preferences_updated",
            aggregate_type="customer",
            aggregate_id=customer_id,
            domain="identity",
            changes={
                k: FieldChange(before=before[k], after=v)
                for k, v in preferences.items()
            },
        )


class AddressService:
    """Manages address operations for a customer.

    All write operations flush within the service but do not commit —
    the caller (route handler) owns the transaction boundary.
    """

    def __init__(self, session: Session, audit: AuditPort) -> None:
        """Initialize the service with an active database session and audit port.

        Args:
            session: The SQLAlchemy session scoped to the current request.
            audit: The audit port used to record state-changing operations.
        """
        self.repo = AddressRepository(session)
        self.customer_repo = CustomerRepository(session)
        self._audit = audit

    def list_addresses(
        self,
        customer_id: uuid.UUID,
        cursor: tuple[datetime, uuid.UUID] | None = None,
    ) -> list[Any]:
        """Return ADDRESS_PAGE_SIZE + 1 active addresses for the given customer.

        Callers must pass the result to paginate() which handles slicing,
        has_more detection, and cursor encoding.

        Raises:
            CustomerNotFound: If no active customer with the given id exists.

        Args:
            customer_id: The UUID of the customer.
            cursor: Keyset cursor (created_at, id) for pagination.
        """
        if self.customer_repo.get_by_id(customer_id) is None:
            raise CustomerNotFound(customer_id)
        return self.repo.list_by_customer(customer_id, ADDRESS_PAGE_SIZE + 1, cursor)

    def add_address(self, customer_id: uuid.UUID, **kwargs: Any) -> Any:
        """Add a new address for the given customer, or return the existing one.

        Idempotent on (customer_id, label) — if an active address with the same
        label already exists, it is returned unchanged.

        Raises:
            CustomerNotFound: If no active customer with the given id exists.

        Args:
            customer_id: The UUID of the customer.
            **kwargs: Address field values.
        """
        if self.customer_repo.get_by_id(customer_id) is None:
            raise CustomerNotFound(customer_id)
        existing = self.repo.get_by_customer_and_label(customer_id, kwargs["label"])
        if existing is not None:
            logger.info(
                "Address already exists for customer %s: %s", customer_id, existing.id
            )
            return existing
        if kwargs.get("is_default"):
            self.repo.clear_default(customer_id)
        address = self.repo.create(customer_id=customer_id, **kwargs)
        logger.info("Address added for customer %s: %s", customer_id, address.id)
        record_audit(
            self._audit,
            actor_id=customer_id,
            operation="create",
            action="customer.address_created",
            aggregate_type="address",
            aggregate_id=address.id,
            domain="identity",
            changes={k: FieldChange(before=None, after=v) for k, v in kwargs.items()},
        )
        return address

    def update_address(
        self, customer_id: uuid.UUID, address_id: uuid.UUID, data: dict[str, Any]
    ) -> Any:
        """Apply a partial update to an address owned by the given customer.

        Raises:
            CustomerNotFound: If no active customer with the given id exists.
            AddressNotFound: If no active address with the given id exists for
                this customer.

        Args:
            customer_id: The UUID of the owning customer.
            address_id: The UUID of the address to update.
            data: A dict of field names to new values.
        """
        if self.customer_repo.get_by_id(customer_id) is None:
            raise CustomerNotFound(customer_id)
        address = self.repo.get_by_id(address_id)
        if address is None or address.customer_id != customer_id:
            raise AddressNotFound(address_id)
        if data.get("is_default"):
            self.repo.clear_default(customer_id)
        before = {k: getattr(address, k) for k in data}
        updated = self.repo.update(address, data)
        record_audit(
            self._audit,
            actor_id=customer_id,
            operation="update",
            action="customer.address_updated",
            aggregate_type="address",
            aggregate_id=address_id,
            domain="identity",
            changes={k: FieldChange(before=before[k], after=data[k]) for k in data},
        )
        return updated

    def remove_address(self, customer_id: uuid.UUID, address_id: uuid.UUID) -> None:
        """Soft-delete an address owned by the given customer.

        Raises:
            CustomerNotFound: If no active customer with the given id exists.
            AddressNotFound: If no active address with the given id exists for
                this customer.

        Args:
            customer_id: The UUID of the owning customer.
            address_id: The UUID of the address to remove.
        """
        if self.customer_repo.get_by_id(customer_id) is None:
            raise CustomerNotFound(customer_id)
        address = self.repo.get_by_id(address_id)
        if address is None or address.customer_id != customer_id:
            raise AddressNotFound(address_id)
        self.repo.delete(address)
        logger.info("Address removed for customer %s: %s", customer_id, address_id)
        record_audit(
            self._audit,
            actor_id=customer_id,
            operation="delete",
            action="customer.address_deleted",
            aggregate_type="address",
            aggregate_id=address_id,
            domain="identity",
            changes=None,
        )
