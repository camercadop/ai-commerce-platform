import uuid
from datetime import UTC, datetime
from typing import Any

from app.inventory.models import InventoryItem, Reservation, ReservationStatus
from app.shared.audit_log import AuditPort, AuditRecord
from app.shared.events import EventEnvelope, MessageBroker


def make_inventory_item(**kwargs: Any) -> InventoryItem:
    """Build an InventoryItem instance with sensible defaults for testing."""
    obj = InventoryItem()
    obj.id = kwargs.get("id", uuid.uuid4())
    obj.variant_id = kwargs.get("variant_id", uuid.uuid4())
    obj.quantity_on_hand = kwargs.get("quantity_on_hand", 0)
    obj.quantity_reserved = kwargs.get("quantity_reserved", 0)
    obj.created_at = kwargs.get("created_at", datetime.now(UTC))
    obj.updated_at = kwargs.get("updated_at", datetime.now(UTC))
    obj.movements = kwargs.get("movements", [])
    obj.reservations = kwargs.get("reservations", [])
    return obj


def make_reservation(**kwargs: Any) -> Reservation:
    """Build a Reservation instance with sensible defaults for testing."""
    obj = Reservation()
    obj.id = kwargs.get("id", uuid.uuid4())
    obj.inventory_item_id = kwargs.get("inventory_item_id", uuid.uuid4())
    obj.order_id = kwargs.get("order_id", uuid.uuid4())
    obj.quantity = kwargs.get("quantity", 1)
    obj.status = kwargs.get("status", ReservationStatus.RESERVED)
    obj.created_at = kwargs.get("created_at", datetime.now(UTC))
    obj.updated_at = kwargs.get("updated_at", datetime.now(UTC))
    return obj


class FakeSession:
    """Minimal fake SQLAlchemy session for repository tests."""

    def __init__(self, store: dict[uuid.UUID, Any]) -> None:
        self._store = store

    def add(self, obj: Any) -> None:
        self._store[obj.id] = obj

    def delete(self, obj: Any) -> None:
        self._store.pop(obj.id, None)

    def flush(self) -> None:
        pass


class FakeInventoryRepository:
    """In-memory InventoryRepository for unit tests."""

    def __init__(self, items: list[InventoryItem] | None = None) -> None:
        self._store: dict[uuid.UUID, InventoryItem] = {i.id: i for i in (items or [])}
        self.session = FakeSession(self._store)

    def get_by_variant(self, variant_id: uuid.UUID) -> InventoryItem | None:
        """Return the inventory item for the given variant, or None."""
        return next(
            (i for i in self._store.values() if i.variant_id == variant_id),
            None,
        )

    def get_by_variant_for_update(self, variant_id: uuid.UUID) -> InventoryItem:
        """Return the inventory item for the given variant with write lock.

        Raises InventoryItemNotFound if not found.
        """
        item = self.get_by_variant(variant_id)
        if item is None:
            from app.inventory.exceptions import InventoryItemNotFound
            raise InventoryItemNotFound(variant_id)
        return item

    def get_by_id_for_update(self, record_id: uuid.UUID) -> InventoryItem:
        """Return the inventory item for the given id with write lock.

        Raises InventoryItemNotFound if not found.
        """
        item = self._store.get(record_id)
        if item is None:
            from app.inventory.exceptions import InventoryItemNotFound
            raise InventoryItemNotFound(record_id)
        return item

    def create(self, **kwargs: Any) -> InventoryItem:
        """Create and store a new inventory item."""
        obj = make_inventory_item(**kwargs)
        self._store[obj.id] = obj
        return obj


class FakeReservationRepository:
    """In-memory ReservationRepository for unit tests."""

    def __init__(self, reservations: list[Reservation] | None = None) -> None:
        self._store: dict[uuid.UUID, Reservation] = {r.id: r for r in (reservations or [])}
        self.session = FakeSession(self._store)

    def get_by_order(self, order_id: uuid.UUID) -> list[Reservation]:
        """Return all reservations for the given order."""
        return [r for r in self._store.values() if r.order_id == order_id]

    def get_by_id(self, reservation_id: uuid.UUID) -> Reservation | None:
        """Return the reservation with the given id, or None."""
        return self._store.get(reservation_id)

    def create(self, **kwargs: Any) -> Reservation:
        """Create and store a new reservation."""
        obj = make_reservation(**kwargs)
        self._store[obj.id] = obj
        return obj


class FakeAuditPort(AuditPort):
    """In-memory AuditPort for unit tests."""

    def __init__(self) -> None:
        self.recorded: list[AuditRecord] = []

    def record(self, entry: AuditRecord) -> None:
        """Capture the audit record for assertion."""
        self.recorded.append(entry)


class RaisingMessageBroker(MessageBroker):
    """Message broker that always raises on publish."""

    def publish(self, topic: str, envelope: EventEnvelope) -> None:
        raise RuntimeError("broker unavailable")

    def subscribe(self, topic: str, handler: Any) -> None:
        pass
