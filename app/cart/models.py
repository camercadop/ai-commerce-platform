import uuid

from sqlalchemy import (
    UUID,
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.shared.db import BaseModel, SoftDeleteMixin, TimestampMixin


class Cart(SoftDeleteMixin, TimestampMixin, BaseModel):
    """A shopping cart identified by session, optionally bound to a customer."""

    __tablename__ = "commerce_cart_carts"

    __table_args__ = (
        Index("idx_cart_carts_customer_id", "customer_id"),
        UniqueConstraint("session_id", name="uq_cart_carts_session_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    # Unique identifier for this cart.

    session_id: Mapped[str] = mapped_column(String(255), nullable=False)
    # Client-supplied session token identifying an anonymous or authenticated cart.

    customer_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
    )
    # Identifier of the authenticated customer who owns this cart, if any.

    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    # Lifecycle status of the cart (active, checked_out, abandoned).

    items: Mapped[list[CartItem]] = relationship(
        "CartItem", back_populates="cart", cascade="all, delete-orphan"
    )
    # Items contained in this cart.


class CartItem(TimestampMixin, BaseModel):
    """A single variant line item within a shopping cart."""

    __tablename__ = "commerce_cart_items"

    __table_args__ = (
        Index("idx_cart_items_cart_id", "cart_id"),
        CheckConstraint("quantity > 0", name="ck_cart_items_positive_quantity"),
        UniqueConstraint(
            "cart_id", "variant_id", name="uq_cart_items_cart_id_variant_id"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    # Unique identifier for this cart item.

    cart_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("commerce_cart_carts.id", name="fk_cart_items_cart_id"),
        nullable=False,
    )
    # Identifier of the cart this item belongs to.

    variant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
    )
    # Identifier of the product variant (cross-domain reference, no FK).

    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    # Quantity of this variant in the cart.

    unit_price: Mapped[object] = mapped_column(Numeric(10, 2), nullable=False)
    # Current catalog price at the time of add or update.

    discount_value: Mapped[object] = mapped_column(
        Numeric(10, 2), nullable=False, default=0
    )
    # Absolute discount applied to this item.

    discount_percent: Mapped[object] = mapped_column(
        Numeric(5, 2), nullable=False, default=0
    )
    # Discount rate applied to this item (0–100).

    tax_value: Mapped[object] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    # Absolute tax amount applied to this item. Zero means tax-free.

    tax_percent: Mapped[object] = mapped_column(
        Numeric(5, 2), nullable=False, default=0
    )
    # Tax rate applied to this item (0–100). Zero means tax-free.

    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    # Item lifecycle status (active, unavailable).

    cart: Mapped[Cart] = relationship("Cart", back_populates="items")
    # The cart this item belongs to.
