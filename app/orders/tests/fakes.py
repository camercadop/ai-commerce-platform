import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from app.orders.models import Order, OrderAdjustment, OrderItem
from app.orders.ports import AdjustmentRuleMatch, AdjustmentRulesPort, CartData, CartPort
from app.shared.audit_log import AuditPort, AuditRecord
from app.shared.events import EventEnvelope, MessageBroker


def make_order(**kwargs: Any) -> Order:
    """Build an Order instance with sensible defaults for testing."""
    obj = Order()
    obj.id = kwargs.get("id", uuid.uuid4())
    obj.cart_id = kwargs.get("cart_id", uuid.uuid4())
    obj.customer_id = kwargs.get("customer_id", None)
    obj.status = kwargs.get("status", "pending")
    obj.subtotal = kwargs.get("subtotal", Decimal("10.00"))
    obj.discount_total = kwargs.get("discount_total", Decimal("0.00"))
    obj.tax_total = kwargs.get("tax_total", Decimal("0.00"))
    obj.total_amount = kwargs.get("total_amount", Decimal("10.00"))
    obj.items = kwargs.get("items", [])
    obj.adjustments = kwargs.get("adjustments", [])
    obj.created_at = kwargs.get("created_at", datetime.now(UTC))
    obj.updated_at = kwargs.get("updated_at", datetime.now(UTC))
    return obj


def make_order_item(**kwargs: Any) -> OrderItem:
    """Build an OrderItem instance with sensible defaults for testing."""
    obj = OrderItem()
    obj.id = kwargs.get("id", uuid.uuid4())
    obj.order_id = kwargs.get("order_id", uuid.uuid4())
    obj.variant_id = kwargs.get("variant_id", uuid.uuid4())
    obj.quantity = kwargs.get("quantity", 1)
    obj.unit_price = kwargs.get("unit_price", Decimal("10.00"))
    obj.discount_value = kwargs.get("discount_value", Decimal("0.00"))
    obj.discount_percent = kwargs.get("discount_percent", Decimal("0.00"))
    obj.tax_value = kwargs.get("tax_value", Decimal("0.00"))
    obj.tax_percent = kwargs.get("tax_percent", Decimal("0.00"))
    obj.created_at = kwargs.get("created_at", datetime.now(UTC))
    obj.updated_at = kwargs.get("updated_at", datetime.now(UTC))
    return obj


def make_cart_data(**kwargs: Any) -> CartData:
    """Build a CartData dict with sensible defaults for testing."""
    return CartData(
        id=kwargs.get("id", uuid.uuid4()),
        customer_id=kwargs.get("customer_id", None),
        status=kwargs.get("status", "active"),
        items=kwargs.get("items", []),
    )


def make_cart_item_data(**kwargs: Any) -> dict[str, Any]:
    """Build a CartItemData dict with sensible defaults for testing."""
    return {
        "variant_id": kwargs.get("variant_id", uuid.uuid4()),
        "quantity": kwargs.get("quantity", 1),
        "unit_price": kwargs.get("unit_price", "10.00"),
        "discount_value": kwargs.get("discount_value", "0.00"),
        "discount_percent": kwargs.get("discount_percent", "0.00"),
        "tax_value": kwargs.get("tax_value", "0.00"),
        "tax_percent": kwargs.get("tax_percent", "0.00"),
    }


class FakeSession:
    """Minimal fake SQLAlchemy session for repository tests."""

    def __init__(self, store: dict[uuid.UUID, Any]) -> None:
        self._store = store
        self._added: list[Any] = []

    def add(self, obj: Any) -> None:
        if obj.id is None:
            obj.id = uuid.uuid4()
        self._store[obj.id] = obj

    def add_all(self, objs: list[Any]) -> None:
        for obj in objs:
            self._store[obj.id] = obj

    def flush(self) -> None:
        pass


class FakeOrderRepository:
    """In-memory OrderRepository for unit tests."""

    def __init__(self, orders: list[Order] | None = None) -> None:
        self._store: dict[uuid.UUID, Order] = {o.id: o for o in (orders or [])}
        self.session = FakeSession(self._store)

    def get_with_items(self, order_id: uuid.UUID) -> Order | None:
        """Return the order with items, or None."""
        return self._store.get(order_id)

    def list_by_customer(self, customer_id: uuid.UUID) -> list[Order]:
        """Return all orders for the given customer."""
        return [o for o in self._store.values() if o.customer_id == customer_id]


class FakeOrderItemRepository:
    """In-memory OrderItemRepository for unit tests."""

    def __init__(self, items: list[OrderItem] | None = None) -> None:
        self._store: dict[uuid.UUID, OrderItem] = {i.id: i for i in (items or [])}
        self.session = FakeSession(self._store)

    def list_by_order(self, order_id: uuid.UUID) -> list[OrderItem]:
        """Return all items for the given order."""
        return [i for i in self._store.values() if i.order_id == order_id]


class FakeCartPort(CartPort):
    """Configurable cart port for unit tests."""

    def __init__(self, cart: CartData | None = None) -> None:
        self._cart = cart

    def get_cart(self, cart_id: uuid.UUID) -> CartData | None:
        """Return the configured cart, or None."""
        return self._cart


class FakeAdjustmentRulesPort(AdjustmentRulesPort):
    """Configurable adjustment rules port for unit tests."""

    def __init__(self, adjustments: list[AdjustmentRuleMatch] | None = None) -> None:
        self._adjustments = adjustments or []

    def get_adjustments(self, order: Order) -> list[AdjustmentRuleMatch]:
        """Return the configured adjustments."""
        return self._adjustments


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
