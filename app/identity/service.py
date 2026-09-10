import logging
import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.identity.exceptions import (
    AddressNotFound,
    CustomerAlreadyExists,
    CustomerNotFound,
)
from app.identity.models import CustomerPreference
from app.identity.repository import AddressRepository, CustomerRepository

logger = logging.getLogger(__name__)


class CustomerService:
    """Manages customer registration and profile operations.

    All write operations flush within the service but do not commit —
    the caller (route handler) owns the transaction boundary.
    """

    def __init__(self, session: Session) -> None:
        """Initialize the service with an active database session.

        Args:
            session: The SQLAlchemy session scoped to the current request.
        """
        self.repo = CustomerRepository(session)
        self.session = session

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

        customer = self.repo.create(
            identity_provider_id=identity_provider_id,
            email=email,
            first_name=first_name,
            last_name=last_name,
        )
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
        return self.repo.update(customer, data)

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

        existing = {pref.key: pref for pref in customer.preferences}
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


class AddressService:
    """Manages address operations for a customer.

    All write operations flush within the service but do not commit —
    the caller (route handler) owns the transaction boundary.
    """

    def __init__(self, session: Session) -> None:
        """Initialize the service with an active database session.

        Args:
            session: The SQLAlchemy session scoped to the current request.
        """
        self.repo = AddressRepository(session)
        self.customer_repo = CustomerRepository(session)

    def list_addresses(self, customer_id: uuid.UUID) -> list[Any]:
        """Return all active addresses for the given customer.

        Raises:
            CustomerNotFound: If no active customer with the given id exists.

        Args:
            customer_id: The UUID of the customer.
        """
        if self.customer_repo.get_by_id(customer_id) is None:
            raise CustomerNotFound(customer_id)
        return self.repo.list_by_customer(customer_id)

    def add_address(self, customer_id: uuid.UUID, **kwargs: Any) -> Any:
        """Add a new address for the given customer.

        Raises:
            CustomerNotFound: If no active customer with the given id exists.

        Args:
            customer_id: The UUID of the customer.
            **kwargs: Address field values.
        """
        if self.customer_repo.get_by_id(customer_id) is None:
            raise CustomerNotFound(customer_id)
        address = self.repo.create(customer_id=customer_id, **kwargs)
        logger.info("Address added for customer %s: %s", customer_id, address.id)
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
        return self.repo.update(address, data)

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
