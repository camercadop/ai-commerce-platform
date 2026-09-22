import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from app.cart.models import Cart, CartItem
from app.cart.ports import CatalogPort, InventoryPort
from app.shared.audit_log import AuditPort, AuditRecord
from app.shared.events import EventEnvelope, MessageBroker


def make_cart(**kwargs: Any) -> Cart:
    """Build a Cart instance with sensible defaults for testing."""
    obj = Cart()
    obj.id = kwargs.get("id", uuid.uuid4())
    obj.session_id = kwargs.get("session_id", "session-1")
    obj.customer_id = kwargs.get("customer_id", None)
    obj.status = kwargs.get("status", "active")
    obj.deleted_at = kwargs.get("deleted_at", None)
    obj.created_at = kwargs.get("created_at", datetime.now(UTC))
    obj.updated_at = kwargs.get("updated_at", datetime.now(UTC))
    obj.items = kwargs.get("items", [])
    return obj


def make_cart_item(**kwargs: Any) -> CartItem:
    """Build a CartItem instance with sensible defaults for testing."""
    obj = CartItem()
    obj.id = kwargs.get("id", uuid.uuid4())
    obj.cart_id = kwargs.get("cart_id", uuid.uuid4())
    obj.variant_id = kwargs.get("variant_id", uuid.uuid4())
    obj.quantity = kwargs.get("quantity", 1)
    obj.unit_price = kwargs.get("unit_price", Decimal("9.99"))
    obj.status = kwargs.get("status", "active")
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


class FakeCartRepository:
    """In-memory CartRepository for unit tests."""

    def __init__(self, carts: list[Cart] | None = None) -> None:
        self._store: dict[uuid.UUID, Cart] = {c.id: c for c in (carts or [])}
        self.session = FakeSession(self._store)

    def get_with_items(self, cart_id: uuid.UUID) -> Cart | None:
        """Return the cart with items loaded, or None."""
        cart = self._store.get(cart_id)
        return cart if cart and cart.deleted_at is None else None

    def get_by_session_id(self, session_id: str) -> Cart | None:
        """Return the active cart for the session, or None."""
        return next(
            (
                c
                for c in self._store.values()
                if c.session_id == session_id and c.deleted_at is None
            ),
            None,
        )

    def get_by_customer_id(self, customer_id: uuid.UUID) -> Cart | None:
        """Return the active cart for the customer, or None."""
        return next(
            (
                c
                for c in self._store.values()
                if c.customer_id == customer_id and c.deleted_at is None
            ),
            None,
        )

    def get_or_create_by_session_id(self, session_id: str) -> Cart:
        """Return the active cart for the session, creating one if needed."""
        cart = self.get_by_session_id(session_id)
        if cart is not None:
            return cart
        cart = make_cart(session_id=session_id)
        self._store[cart.id] = cart
        return cart


class FakeCartItemRepository:
    """In-memory CartItemRepository for unit tests."""

    def __init__(self, items: list[CartItem] | None = None) -> None:
        self._store: dict[uuid.UUID, CartItem] = {i.id: i for i in (items or [])}
        self.session = FakeSession(self._store)

    def get_by_cart_and_variant(
        self, cart_id: uuid.UUID, variant_id: uuid.UUID
    ) -> CartItem | None:
        """Return the cart item for the given cart and variant, or None."""
        return next(
            (
                i
                for i in self._store.values()
                if i.cart_id == cart_id and i.variant_id == variant_id
            ),
            None,
        )


class FakeAuditPort(AuditPort):
    """In-memory AuditPort for unit tests."""

    def __init__(self) -> None:
        self.recorded: list[AuditRecord] = []

    def record(self, entry: AuditRecord) -> None:
        """Capture the audit record for assertion."""
        self.recorded.append(entry)


class FakeCatalogPort(CatalogPort):
    """Configurable catalog port for unit tests."""

    def __init__(self, prices: dict[uuid.UUID, Decimal] | None = None) -> None:
        self._prices = prices or {}

    def get_variant_price(self, variant_id: uuid.UUID) -> Decimal | None:
        """Return the configured price for the variant, or None."""
        return self._prices.get(variant_id)


class FakeInventoryPort(InventoryPort):
    """Configurable inventory port for unit tests."""

    def __init__(self, availability: dict[uuid.UUID, bool] | None = None) -> None:
        self._availability = availability or {}

    def check_availability(self, variant_id: uuid.UUID, quantity: int) -> bool:
        """Return the configured availability for the variant."""
        return self._availability.get(variant_id, True)


class RaisingMessageBroker(MessageBroker):
    """Message broker that always raises on publish."""

    def publish(self, topic: str, envelope: EventEnvelope) -> None:
        raise RuntimeError("broker unavailable")

    def subscribe(self, topic: str, handler: Any) -> None:
        pass
