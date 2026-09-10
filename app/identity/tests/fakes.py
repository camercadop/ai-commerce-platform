import uuid
from datetime import UTC, datetime

from app.identity.models import Address, Customer, CustomerPreference


def make_customer(**kwargs: object) -> Customer:
    """Build a Customer instance with sensible defaults for testing."""
    customer = Customer()
    customer.id = kwargs.get("id", uuid.uuid4())  # type: ignore[assignment]
    customer.identity_provider_id = kwargs.get("identity_provider_id", "sub-123")  # type: ignore[assignment]
    customer.email = kwargs.get("email", "test@example.com")  # type: ignore[assignment]
    customer.first_name = kwargs.get("first_name", "Jane")  # type: ignore[assignment]
    customer.last_name = kwargs.get("last_name", "Doe")  # type: ignore[assignment]
    customer.deleted_at = kwargs.get("deleted_at")  # type: ignore[assignment]
    customer.created_at = kwargs.get("created_at", datetime.now(UTC))  # type: ignore[assignment]
    customer.updated_at = kwargs.get("updated_at", datetime.now(UTC))  # type: ignore[assignment]
    customer.addresses = kwargs.get("addresses", [])  # type: ignore[assignment]
    customer.preferences = kwargs.get("preferences", [])  # type: ignore[assignment]
    return customer


def make_address(**kwargs: object) -> Address:
    """Build an Address instance with sensible defaults for testing."""
    address = Address()
    address.id = kwargs.get("id", uuid.uuid4())  # type: ignore[assignment]
    address.customer_id = kwargs.get("customer_id", uuid.uuid4())  # type: ignore[assignment]
    address.label = kwargs.get("label", "Home")  # type: ignore[assignment]
    address.street = kwargs.get("street", "123 Main St")  # type: ignore[assignment]
    address.city = kwargs.get("city", "Springfield")  # type: ignore[assignment]
    address.state = kwargs.get("state", "IL")  # type: ignore[assignment]
    address.country = kwargs.get("country", "US")  # type: ignore[assignment]
    address.postal_code = kwargs.get("postal_code", "62701")  # type: ignore[assignment]
    address.is_default = kwargs.get("is_default", False)  # type: ignore[assignment]
    address.deleted_at = kwargs.get("deleted_at")  # type: ignore[assignment]
    address.created_at = kwargs.get("created_at", datetime.now(UTC))  # type: ignore[assignment]
    address.updated_at = kwargs.get("updated_at", datetime.now(UTC))  # type: ignore[assignment]
    return address


class FakeCustomerRepository:
    """In-memory CustomerRepository for unit tests."""

    def __init__(self, customers: list[Customer] | None = None) -> None:
        self._store: dict[uuid.UUID, Customer] = {
            c.id: c for c in (customers or [])
        }

    def get_by_id(self, record_id: uuid.UUID) -> Customer | None:
        """Return the customer with the given id, or None."""
        c = self._store.get(record_id)
        return c if c and c.deleted_at is None else None

    def get_by_identity_provider_id(self, identity_provider_id: str) -> Customer | None:
        """Return the customer matching the given identity_provider_id, or None."""
        return next(
            (
                c for c in self._store.values()
                if c.identity_provider_id == identity_provider_id
                and c.deleted_at is None
            ),
            None,
        )

    def create(self, **kwargs: object) -> Customer:
        """Create and store a new customer."""
        customer = make_customer(**kwargs)
        self._store[customer.id] = customer
        return customer

    def update(self, record: Customer, data: dict[str, object]) -> Customer:
        """Apply a partial update to the given customer."""
        for key, value in data.items():
            setattr(record, key, value)
        return record

    def delete(self, record: Customer) -> None:
        """Soft-delete the given customer."""
        record.deleted_at = datetime.now(UTC)


class FakeAddressRepository:
    """In-memory AddressRepository for unit tests."""

    def __init__(self, addresses: list[Address] | None = None) -> None:
        self._store: dict[uuid.UUID, Address] = {
            a.id: a for a in (addresses or [])
        }

    def get_by_id(self, record_id: uuid.UUID) -> Address | None:
        """Return the address with the given id, or None."""
        a = self._store.get(record_id)
        return a if a and a.deleted_at is None else None

    def list_by_customer(self, customer_id: uuid.UUID) -> list[Address]:
        """Return all active addresses for the given customer."""
        return [
            a for a in self._store.values()
            if a.customer_id == customer_id and a.deleted_at is None
        ]

    def create(self, **kwargs: object) -> Address:
        """Create and store a new address."""
        address = make_address(**kwargs)
        self._store[address.id] = address
        return address

    def update(self, record: Address, data: dict[str, object]) -> Address:
        """Apply a partial update to the given address."""
        for key, value in data.items():
            setattr(record, key, value)
        return record

    def delete(self, record: Address) -> None:
        """Soft-delete the given address."""
        record.deleted_at = datetime.now(UTC)


class FakeCustomerPreferenceSession:
    """Minimal session fake that tracks added CustomerPreference instances."""

    def __init__(self) -> None:
        self.added: list[CustomerPreference] = []

    def add(self, obj: object) -> None:
        """Track added objects."""
        if isinstance(obj, CustomerPreference):
            self.added.append(obj)

    def flush(self) -> None:
        """No-op flush."""
