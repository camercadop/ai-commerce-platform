import uuid
from datetime import datetime

from sqlalchemy import update

from app.identity.models import Address, Customer, CustomerPreference
from app.shared.db import BaseRepository


class CustomerRepository(BaseRepository[Customer]):
    """Repository for Customer persistence operations.

    Provides lookup by identity provider subject in addition to the base
    CRUD interface. All queries exclude soft-deleted records.
    """

    model_class = Customer

    def get_by_identity_provider_id(self, identity_provider_id: str) -> Customer | None:
        """Return the active customer matching the given identity provider subject.

        Returns None if no customer exists or the record has been soft-deleted.

        Args:
            identity_provider_id: The JWT subject claim from the identity provider.
        """
        return self.find_one_by(identity_provider_id=identity_provider_id)

    def upsert_preference(self, customer_id: uuid.UUID, key: str, value: str) -> None:
        """Insert or update a single preference for the given customer.

        Args:
            customer_id: The UUID of the owning customer.
            key: The preference key.
            value: The preference value.
        """
        customer = self.get_by_id(customer_id)
        if customer is None:
            return
        existing = next((p for p in customer.preferences if p.key == key), None)
        if existing is not None:
            existing.value = value
        else:
            self.session.add(
                CustomerPreference(customer_id=customer_id, key=key, value=value)
            )
        self.session.flush()


class AddressRepository(BaseRepository[Address]):
    """Repository for Address persistence operations.

    Provides listing by customer in addition to the base CRUD interface.
    All queries exclude soft-deleted records.
    """

    model_class = Address

    def list_by_customer(
        self,
        customer_id: uuid.UUID,
        limit: int,
        cursor: tuple[datetime, uuid.UUID] | None = None,
    ) -> list[Address]:
        """Return a page of active addresses belonging to the given customer.

        Args:
            customer_id: The UUID of the owning customer.
            limit: Maximum number of records to return.
            cursor: Exclusive lower bound as (created_at, id) for keyset pagination.
        """
        return self.list_page(
            Address.customer_id == customer_id, limit=limit, cursor=cursor
        )

    def get_by_customer_and_label(
        self, customer_id: uuid.UUID, label: str
    ) -> Address | None:
        """Return the active address matching the given customer and label, or None.

        Args:
            customer_id: The UUID of the owning customer.
            label: The address label (e.g. Home, Work).
        """
        return self.find_one_by(customer_id=customer_id, label=label)

    def clear_default(self, customer_id: uuid.UUID) -> None:
        """Unset is_default on all active addresses for the given customer.

        Args:
            customer_id: The UUID of the owning customer.
        """
        stmt = (
            update(Address)
            .where(Address.customer_id == customer_id)
            .where(Address.deleted_at.is_(None))
            .values(is_default=False)
        )
        self.session.execute(stmt)
