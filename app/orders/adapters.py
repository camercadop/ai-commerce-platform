import uuid
from typing import TYPE_CHECKING

from app.orders.ports import (
    AdjustmentRuleMatch,
    AdjustmentRulesPort,
    CartData,
    CartPort,
)

if TYPE_CHECKING:
    from app.orders.models import Order


class StubCartPort(CartPort):
    """No-op cart port that always returns None.

    Use in tests and local development where a real cart service is
    not available. Never use in production.
    """

    def get_cart(self, cart_id: uuid.UUID) -> CartData | None:
        return None


class StubAdjustmentRulesPort(AdjustmentRulesPort):
    """No-op adjustment rules port that always returns an empty list.

    Use in tests and local development where no adjustment rules are
    configured. Never use in production.
    """

    def get_adjustments(self, order: Order) -> list[AdjustmentRuleMatch]:
        return []
