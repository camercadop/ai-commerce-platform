import uuid
from decimal import Decimal

import pytest

from app.orders.exceptions import (
    CartHasNoItems,
    CartNotEligibleForCheckout,
    InvalidCartReference,
    OrderNotFound,
)
from app.orders.models import Order
from app.orders.ports import AdjustmentRuleMatch
from app.orders.service import OrderService
from app.orders.tests.fakes import (
    FakeAdjustmentRulesPort,
    FakeAuditPort,
    FakeCartPort,
    FakeOrderItemRepository,
    FakeOrderRepository,
    RaisingMessageBroker,
    make_cart_data,
    make_cart_item_data,
    make_order,
)
from app.shared.events import MessageBroker, NoOpMessageBroker


def _order_service(
    orders: list[Order] | None = None,
    cart_data: object = None,
    adjustments: list[AdjustmentRuleMatch] | None = None,
    audit: FakeAuditPort | None = None,
    broker: MessageBroker | None = None,
) -> OrderService:
    return OrderService(
        order_repo=FakeOrderRepository(orders),
        order_item_repo=FakeOrderItemRepository(),
        cart_port=FakeCartPort(cart_data),
        audit=audit or FakeAuditPort(),
        broker=broker or NoOpMessageBroker(),
        adjustment_rules_port=FakeAdjustmentRulesPort(adjustments),
    )


# ---------------------------------------------------------------------------
# OrderService.place_order
# ---------------------------------------------------------------------------


class TestOrderServicePlaceOrder:
    def test_raises_if_cart_not_found(self) -> None:
        svc = _order_service(cart_data=None)

        with pytest.raises(InvalidCartReference):
            svc.place_order(cart_id=uuid.uuid4())

    def test_raises_if_cart_not_active(self) -> None:
        cart = make_cart_data(status="checked_out")
        svc = _order_service(cart_data=cart)

        with pytest.raises(CartNotEligibleForCheckout):
            svc.place_order(cart_id=cart["id"])

    def test_raises_if_cart_has_no_items(self) -> None:
        cart = make_cart_data(items=[])
        svc = _order_service(cart_data=cart)

        with pytest.raises(CartHasNoItems):
            svc.place_order(cart_id=cart["id"])

    def test_creates_order_with_correct_totals(self) -> None:
        item = make_cart_item_data(
            unit_price="10.00",
            quantity=2,
            discount_value="1.00",
            tax_value="0.50",
        )
        cart = make_cart_data(items=[item])
        svc = _order_service(cart_data=cart)

        order = svc.place_order(cart_id=cart["id"])

        assert order.subtotal == Decimal("20.00")
        assert order.discount_total == Decimal("1.00")
        assert order.tax_total == Decimal("0.50")
        assert order.total_amount == Decimal("19.50")

    def test_snapshots_customer_id_from_cart(self) -> None:
        customer_id = uuid.uuid4()
        item = make_cart_item_data()
        cart = make_cart_data(customer_id=customer_id, items=[item])
        svc = _order_service(cart_data=cart)

        order = svc.place_order(cart_id=cart["id"])

        assert order.customer_id == customer_id

    def test_order_status_is_pending(self) -> None:
        item = make_cart_item_data()
        cart = make_cart_data(items=[item])
        svc = _order_service(cart_data=cart)

        order = svc.place_order(cart_id=cart["id"])

        assert order.status == "pending"

    def test_applies_deduction_adjustment(self) -> None:
        item = make_cart_item_data(unit_price="100.00", quantity=1)
        cart = make_cart_data(items=[item])
        adjustment: AdjustmentRuleMatch = {
            "name": "reteiva",
            "kind": "deduction",
            "percent": Decimal("15.00"),
            "value": Decimal("15.00"),
        }
        svc = _order_service(cart_data=cart, adjustments=[adjustment])

        order = svc.place_order(cart_id=cart["id"])

        assert order.total_amount == Decimal("85.00")

    def test_applies_surcharge_adjustment(self) -> None:
        item = make_cart_item_data(unit_price="100.00", quantity=1)
        cart = make_cart_data(items=[item])
        adjustment: AdjustmentRuleMatch = {
            "name": "handling_fee",
            "kind": "surcharge",
            "percent": Decimal("5.00"),
            "value": Decimal("5.00"),
        }
        svc = _order_service(cart_data=cart, adjustments=[adjustment])

        order = svc.place_order(cart_id=cart["id"])

        assert order.total_amount == Decimal("105.00")

    def test_applies_multiple_adjustments(self) -> None:
        item = make_cart_item_data(unit_price="100.00", quantity=1)
        cart = make_cart_data(items=[item])
        adjustments: list[AdjustmentRuleMatch] = [
            {
                "name": "reteiva",
                "kind": "deduction",
                "percent": Decimal("15.00"),
                "value": Decimal("15.00"),
            },
            {
                "name": "reteica",
                "kind": "deduction",
                "percent": Decimal("5.00"),
                "value": Decimal("5.00"),
            },
        ]
        svc = _order_service(cart_data=cart, adjustments=adjustments)

        order = svc.place_order(cart_id=cart["id"])

        assert order.total_amount == Decimal("80.00")

    def test_total_amount_unchanged_when_no_adjustments(self) -> None:
        item = make_cart_item_data(unit_price="50.00", quantity=1)
        cart = make_cart_data(items=[item])
        svc = _order_service(cart_data=cart, adjustments=[])

        order = svc.place_order(cart_id=cart["id"])

        assert order.total_amount == Decimal("50.00")

    def test_broker_failure_does_not_raise(self) -> None:
        item = make_cart_item_data()
        cart = make_cart_data(items=[item])
        svc = _order_service(cart_data=cart, broker=RaisingMessageBroker())

        order = svc.place_order(cart_id=cart["id"])

        assert order.id is not None

    def test_records_audit_when_actor_id_provided(self) -> None:
        item = make_cart_item_data()
        cart = make_cart_data(items=[item])
        audit = FakeAuditPort()
        svc = _order_service(cart_data=cart, audit=audit)

        svc.place_order(cart_id=cart["id"], actor_id=uuid.uuid4())

        assert len(audit.recorded) == 1

    def test_skips_audit_when_actor_id_is_none(self) -> None:
        item = make_cart_item_data()
        cart = make_cart_data(items=[item])
        audit = FakeAuditPort()
        svc = _order_service(cart_data=cart, audit=audit)

        svc.place_order(cart_id=cart["id"], actor_id=None)

        assert len(audit.recorded) == 0


# ---------------------------------------------------------------------------
# OrderService.get_order
# ---------------------------------------------------------------------------


class TestOrderServiceGetOrder:
    def test_returns_order(self) -> None:
        order = make_order()
        svc = _order_service(orders=[order])

        result = svc.get_order(order.id)

        assert result.id == order.id

    def test_raises_if_order_not_found(self) -> None:
        svc = _order_service()

        with pytest.raises(OrderNotFound):
            svc.get_order(uuid.uuid4())
