import logging
import uuid
from decimal import Decimal

from app.orders.events import publish_order_placed
from app.orders.exceptions import (
    CartHasNoItems,
    CartNotEligibleForCheckout,
    InvalidCartReference,
    OrderNotFound,
)
from app.orders.models import Order, OrderAdjustment, OrderItem
from app.orders.ports import AdjustmentRulesPort, CartPort
from app.orders.repository import OrderItemRepository, OrderRepository
from app.shared.audit_log import AuditPort, FieldChange, record_audit
from app.shared.events import MessageBroker

logger = logging.getLogger(__name__)


class OrderService:
    """Manages order creation and retrieval."""

    def __init__(
        self,
        order_repo: OrderRepository,
        order_item_repo: OrderItemRepository,
        cart_port: CartPort,
        audit: AuditPort,
        broker: MessageBroker,
        adjustment_rules_port: AdjustmentRulesPort,
    ) -> None:
        self.order_repo = order_repo
        self.order_item_repo = order_item_repo
        self._cart_port = cart_port
        self._audit = audit
        self._broker = broker
        self._adjustment_rules_port = adjustment_rules_port

    def place_order(
        self, cart_id: uuid.UUID, actor_id: uuid.UUID | None = None
    ) -> Order:
        """Create an order from an active cart checkout.

        Snapshots cart items, evaluates adjustment rules, and computes the
        final total_amount including all deductions and surcharges.

        Args:
            cart_id: UUID of the cart to checkout.
            actor_id: UUID of the actor performing the operation, or None.

        Returns:
            The newly created Order instance with items and adjustments loaded.

        Raises:
            InvalidCartReference: If the cart does not exist.
            CartNotEligibleForCheckout: If the cart is not in active status.
            CartHasNoItems: If the cart has no items.
        """
        cart = self._cart_port.get_cart(cart_id)
        if cart is None:
            raise InvalidCartReference(cart_id)
        if cart["status"] != "active":
            raise CartNotEligibleForCheckout(f"Cart is not active: {cart['status']}")
        if not cart["items"]:
            raise CartHasNoItems("Cart has no items")

        subtotal = sum(
            Decimal(item["unit_price"]) * item["quantity"] for item in cart["items"]
        )
        discount_total = sum(Decimal(item["discount_value"]) for item in cart["items"])
        tax_total = sum(Decimal(item["tax_value"]) for item in cart["items"])
        total_amount = Decimal(subtotal - discount_total + tax_total)

        order = Order(
            cart_id=cart_id,
            customer_id=cart["customer_id"],
            status="pending",
            subtotal=subtotal,
            discount_total=discount_total,
            tax_total=tax_total,
            total_amount=total_amount,
        )
        self.order_repo.session.add(order)
        self.order_repo.session.flush()

        order_items = [
            OrderItem(
                order_id=order.id,
                variant_id=item["variant_id"],
                quantity=item["quantity"],
                unit_price=Decimal(item["unit_price"]),
                discount_value=Decimal(item["discount_value"]),
                discount_percent=Decimal(item["discount_percent"]),
                tax_value=Decimal(item["tax_value"]),
                tax_percent=Decimal(item["tax_percent"]),
            )
            for item in cart["items"]
        ]
        self.order_item_repo.session.add_all(order_items)
        self.order_repo.session.flush()

        adjustments = self._adjustment_rules_port.get_adjustments(order)
        if adjustments:
            order_adjustments = [
                OrderAdjustment(
                    order_id=order.id,
                    name=adj["name"],
                    kind=adj["kind"],
                    percent=adj["percent"],
                    value=adj["value"],
                )
                for adj in adjustments
            ]
            self.order_repo.session.add_all(order_adjustments)

            deductions = sum(
                adj["value"] for adj in adjustments if adj["kind"] == "deduction"
            )
            surcharges = sum(
                adj["value"] for adj in adjustments if adj["kind"] == "surcharge"
            )
            order.total_amount = Decimal(total_amount - deductions + surcharges)
            self.order_repo.session.flush()

        logger.info("Order created: %s", order.id)
        publish_order_placed(
            self._broker,
            order.id,
            cart_id,
            cart["customer_id"],
            Decimal(order.total_amount),  # type: ignore[arg-type]
            len(cart["items"]),
        )
        if actor_id is not None:
            record_audit(
                self._audit,
                actor_id=actor_id,
                operation="create",
                action="orders.order.placed",
                aggregate_type="order",
                aggregate_id=order.id,
                domain="orders",
                changes={
                    "cart_id": FieldChange(before=None, after=str(cart_id)),
                    "customer_id": FieldChange(
                        before=None,
                        after=str(cart["customer_id"]) if cart["customer_id"] else None,
                    ),
                    "total_amount": FieldChange(
                        before=None, after=str(order.total_amount)
                    ),
                    "status": FieldChange(before=None, after="pending"),
                    "items_count": FieldChange(before=None, after=len(cart["items"])),
                },
            )
        return order

    def get_order(self, order_id: uuid.UUID) -> Order:
        """Return the order with its items and adjustments eagerly loaded.

        Args:
            order_id: UUID of the order.

        Returns:
            The Order instance with items and adjustments loaded.

        Raises:
            OrderNotFound: If the order does not exist.
        """
        order = self.order_repo.get_with_items(order_id)
        if order is None:
            raise OrderNotFound(order_id)
        return order
