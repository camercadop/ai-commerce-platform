import uuid
from datetime import UTC, datetime

from app.identity.models import Address, Customer, CustomerPreference
from app.shared.audit_log import AuditPort, AuditRecord


def make_customer(**kwargs: object) -> Customer:
    """Build a Customer instance with sensible defaults for testing."""
    customer = Customer()
    customer.id = kwargs.get("id", uuid.uuid4())
    customer.identity_provider_id = kwargs.get("identity_provider_id", "sub-123")
    customer.email = kwargs.get("email", "test@example.com")
    customer.first_name = kwargs.get("first_name", "Jane")
    customer.last_name = kwargs.get("last_name", "Doe")
    customer.deleted_at = kwargs.get("deleted_at")
    customer.created_at = kwargs.get("created_at", datetime.now(UTC))
    customer.updated_at = kwargs.get("updated_at", datetime.now(UTC))
    customer.addresses = kwargs.get("addresses", [])
    customer.preferences = kwargs.get("preferences", [])
    return customer


def make_address(**kwargs: object) -> Address:
    """Build an Address instance with sensible defaults for testing."""
    address = Address()
    address.id = kwargs.get("id", uuid.uuid4())
    address.customer_id = kwargs.get("customer_id", uuid.uuid4())
    address.label = kwargs.get("label", "Home")
    address.street = kwargs.get("street", "123 Main St")
    address.city = kwargs.get("city", "Springfield")
    address.state = kwargs.get("state", "IL")
    address.country = kwargs.get("country", "US")
    address.postal_code = kwargs.get("postal_code", "62701")
    address.is_default = kwargs.get("is_default", False)
    address.deleted_at = kwargs.get("deleted_at")
    address.created_at = kwargs.get("created_at", datetime.now(UTC))
    address.updated_at = kwargs.get("updated_at", datetime.now(UTC))
    return address


class FakeAuditPort(AuditPort):
    """In-memory AuditPort for unit tests."""

    def __init__(self) -> None:
        self.recorded: list[AuditRecord] = []

    def record(self, entry: AuditRecord) -> None:
        """Capture the audit record for assertion."""
        self.recorded.append(entry)


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

    def upsert_preference(self, customer_id: uuid.UUID, key: str, value: str) -> None:
        """Insert or update a preference for the given customer."""
        customer = self.get_by_id(customer_id)
        if customer is None:
            return
        existing = next((p for p in customer.preferences if p.key == key), None)
        if existing is not None:
            existing.value = value
        else:
            pref = CustomerPreference()
            pref.key = key
            pref.value = value
            customer.preferences.append(pref)


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

    def get_by_customer_and_label(
        self, customer_id: uuid.UUID, label: str
    ) -> Address | None:
        """Return the active address matching customer_id and label, or None."""
        return next(
            (
                a for a in self._store.values()
                if a.customer_id == customer_id
                and a.label == label
                and a.deleted_at is None
            ),
            None,
        )

    def clear_default(self, customer_id: uuid.UUID) -> None:
        """Unset is_default on all active addresses for the given customer."""
        for a in self._store.values():
            if a.customer_id == customer_id and a.deleted_at is None:
                a.is_default = False

    def list_by_customer(
        self,
        customer_id: uuid.UUID,
        limit: int | None = None,
        cursor: object = None,
    ) -> list[Address]:
        """Return active addresses for the given customer."""
        results = [
            a for a in self._store.values()
            if a.customer_id == customer_id and a.deleted_at is None
        ]
        return results[:limit] if limit is not None else results

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
