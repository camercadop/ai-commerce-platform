import uuid

from sqlalchemy import select

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

    def list_by_customer(self, customer_id: uuid.UUID) -> list[Address]:
        """Return all active addresses belonging to the given customer.

        Soft-deleted addresses are excluded from the result.

        Args:
            customer_id: The UUID of the owning customer.
        """
        stmt = (
            select(Address)
            .where(Address.customer_id == customer_id)
            .where(Address.deleted_at.is_(None))
        )
        return list(self.session.execute(stmt).scalars().all())
