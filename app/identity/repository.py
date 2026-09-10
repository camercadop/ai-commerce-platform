import uuid
from datetime import datetime

from sqlalchemy import select, update

from app.identity.models import Address, Customer
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
        stmt = (
            select(Customer)
            .where(Customer.identity_provider_id == identity_provider_id)
            .where(Customer.deleted_at.is_(None))
        )
        return self.session.execute(stmt).scalar_one_or_none()


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
        stmt = (
            select(Address)
            .where(Address.customer_id == customer_id)
            .where(Address.label == label)
            .where(Address.deleted_at.is_(None))
        )
        return self.session.execute(stmt).scalar_one_or_none()

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
