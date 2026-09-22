import uuid
from abc import ABC, abstractmethod
from decimal import Decimal
from typing import TYPE_CHECKING, TypedDict

if TYPE_CHECKING:
    from app.orders.models import Order


class CartItemData(TypedDict):
    """Item details required to snapshot a cart for checkout."""

    variant_id: uuid.UUID
    quantity: int
    unit_price: str
    discount_value: str
    discount_percent: str
    tax_value: str
    tax_percent: str


class CartData(TypedDict):
    """Cart data required to create an order from checkout."""

    id: uuid.UUID
    customer_id: uuid.UUID | None
    status: str
    items: list[CartItemData]


class CartPort(ABC):
    """Abstract port for reading cart data during checkout.

    The concrete implementation lives outside app/orders/ (e.g. app/cart/).
    Domain code must never depend on a concrete implementation directly.
    """

    @abstractmethod
    def get_cart(self, cart_id: uuid.UUID) -> CartData | None:
        """Return the cart with items, or None if not found.

        Args:
            cart_id: The UUID of the cart to load.

        Returns:
            Cart data including line items, or None if the cart does not exist.
        """


class AdjustmentRuleMatch(TypedDict):
    """A resolved adjustment to apply to an order.

    Returned by AdjustmentRulesPort after evaluating active rules against
    the full order. The port is responsible for computing `value` before
    returning.
    """

    name: str
    kind: str
    percent: Decimal
    value: Decimal


class AdjustmentRulesPort(ABC):
    """Abstract port for evaluating order adjustment rules at checkout.

    The concrete implementation queries active AdjustmentRule records and
    evaluates their conditions against the full order. Use StubAdjustmentRulesPort
    in tests and local development where no rules are configured.
    """

    @abstractmethod
    def get_adjustments(self, order: Order) -> list[AdjustmentRuleMatch]:
        """Return all adjustments that apply to the given order.

        Called after order items are flushed so totals are available.
        The port computes each adjustment value before returning.

        Args:
            order: The fully flushed Order instance including items.

        Returns:
            List of adjustments to persist, or an empty list if none apply.
        """
