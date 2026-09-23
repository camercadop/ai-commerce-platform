import uuid
from enum import StrEnum
from typing import Any

from sqlalchemy import (
    UUID,
    Boolean,
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.shared.db import BaseModel, TimestampMixin


class AdjustmentKind(StrEnum):
    """Valid kinds for an AdjustmentRule or OrderAdjustment record."""

    DEDUCTION = "deduction"
    SURCHARGE = "surcharge"


class AdjustmentRule(TimestampMixin, BaseModel):
    """A configurable rule that determines automatic order-level adjustments.

    Rules are evaluated at checkout time against the full order. The `conditions`
    field holds arbitrary matching criteria interpreted by `AdjustmentRulesPort`.
    Only active rules are evaluated.
    """

    __tablename__ = "order_adjustment_rules"

    __table_args__ = (
        Index("idx_orders_adjustment_rules_active", "active"),
        CheckConstraint(
            "kind IN ('deduction', 'surcharge')",
            name="ck_orders_adjustment_rules_kind",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    # Unique identifier for this rule.

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    # Human-readable label for the adjustment (e.g. "reteiva", "reteica").

    kind: Mapped[str] = mapped_column(String(20), nullable=False)
    # Whether this adjustment reduces or increases the total.
    # Must be an AdjustmentKind value.

    percent: Mapped[object] = mapped_column(Numeric(5, 2), nullable=False)
    # Rate applied to the order total to compute the adjustment value (0-100).

    conditions: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default="{}"
    )
    # Arbitrary matching criteria evaluated by AdjustmentRulesPort against
    # the full Order. An empty object means the rule applies unconditionally.

    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    # Whether this rule is currently enforced. Inactive rules are never evaluated.


class Order(TimestampMixin, BaseModel):
    """A customer order created from a cart checkout."""

    __tablename__ = "orders"

    __table_args__ = (
        Index("idx_orders_orders_customer_id", "customer_id"),
        Index("idx_orders_orders_cart_id", "cart_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    # Unique identifier for this order.

    cart_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
    )
    # Identifier of the cart that was checked out (cross-domain reference, no FK).

    customer_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
    )
    # Identifier of the customer who placed the order, if any.

    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    # Lifecycle status of the order (pending, confirmed, cancelled).

    subtotal: Mapped[object] = mapped_column(Numeric(10, 2), nullable=False)
    # Sum of (unit_price * quantity) for all items before discounts and taxes.

    discount_total: Mapped[object] = mapped_column(Numeric(10, 2), nullable=False)
    # Sum of discount_value across all items.

    tax_total: Mapped[object] = mapped_column(Numeric(10, 2), nullable=False)
    # Sum of tax_value across all items.

    total_amount: Mapped[object] = mapped_column(Numeric(10, 2), nullable=False)
    # Final payable amount including adjustments:
    # subtotal - discount_total + tax_total - deductions + surcharges.

    items: Mapped[list[OrderItem]] = relationship(
        "OrderItem",
        back_populates="order",
        cascade="all, delete-orphan",
    )
    # Line items contained in this order.

    adjustments: Mapped[list[OrderAdjustment]] = relationship(
        "OrderAdjustment",
        back_populates="order",
        cascade="all, delete-orphan",
    )
    # Order-level adjustments computed automatically at checkout time.


class OrderItem(TimestampMixin, BaseModel):
    """A single variant line item within an order."""

    __tablename__ = "order_items"

    __table_args__ = (Index("idx_orders_items_order_id", "order_id"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    # Unique identifier for this order item.

    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("orders.id", name="fk_orders_items_order_id"),
        nullable=False,
    )
    # Identifier of the order this item belongs to.

    variant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
    )
    # Identifier of the product variant (cross-domain reference, no FK).

    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    # Quantity of this variant in the order.

    unit_price: Mapped[object] = mapped_column(Numeric(10, 2), nullable=False)
    # Catalog price snapshotted at checkout time.

    discount_value: Mapped[object] = mapped_column(Numeric(10, 2), nullable=False)
    # Absolute discount snapshotted from cart at checkout time.

    discount_percent: Mapped[object] = mapped_column(Numeric(5, 2), nullable=False)
    # Discount rate snapshotted from cart at checkout time (0-100).

    tax_value: Mapped[object] = mapped_column(Numeric(10, 2), nullable=False)
    # Absolute tax amount snapshotted from cart at checkout time. Zero means tax-free.

    tax_percent: Mapped[object] = mapped_column(Numeric(5, 2), nullable=False)
    # Tax rate snapshotted from cart at checkout time (0-100). Zero means tax-free.

    order: Mapped[Order] = relationship("Order", back_populates="items")
    # The order this item belongs to.


class OrderAdjustment(TimestampMixin, BaseModel):
    """An order-level financial adjustment computed automatically at checkout.

    Represents named deductions (e.g. reteiva, reteica) or surcharges derived
    from active AdjustmentRule records. The kind field determines whether the
    value reduces or increases the final payable total.
    """

    __tablename__ = "order_adjustments"

    __table_args__ = (Index("idx_orders_adjustments_order_id", "order_id"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    # Unique identifier for this adjustment.

    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("orders.id", name="fk_orders_adjustments_order_id"),
        nullable=False,
    )
    # Identifier of the order this adjustment belongs to.

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    # Human-readable name of the adjustment (e.g. "reteiva", "reteica").

    kind: Mapped[str] = mapped_column(String(20), nullable=False)
    # Whether this adjustment reduces or increases the total.
    # Must be an AdjustmentKind value.

    percent: Mapped[object] = mapped_column(Numeric(5, 2), nullable=False)
    # Rate used to compute the adjustment value (0-100).

    value: Mapped[object] = mapped_column(Numeric(10, 2), nullable=False)
    # Computed adjustment amount snapshotted at the time of application.

    order: Mapped[Order] = relationship("Order", back_populates="adjustments")
    # The order this adjustment belongs to.
