import uuid
from enum import StrEnum

from sqlalchemy import (
    UUID,
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.shared.db import BaseModel, TimestampMixin


class MovementKind(StrEnum):
    """Valid kinds for a StockMovement record."""

    ADJUSTMENT = "adjustment"
    RESERVATION = "reservation"
    RELEASE = "release"
    CONFIRMATION = "confirmation"


class ReservationStatus(StrEnum):
    """Valid lifecycle statuses for a Reservation record."""

    RESERVED = "reserved"
    CONFIRMED = "confirmed"
    RELEASED = "released"


class InventoryItem(TimestampMixin, BaseModel):
    """Tracked stock quantity for a product variant."""

    __tablename__ = "inventory_items"

    __table_args__ = (
        UniqueConstraint("variant_id", name="uq_inventory_items_variant_id"),
        CheckConstraint(
            "quantity_on_hand >= 0", name="ck_inventory_items_non_negative_on_hand"
        ),
        CheckConstraint(
            "quantity_reserved >= 0", name="ck_inventory_items_non_negative_reserved"
        ),
        Index("idx_inventory_items_variant_id", "variant_id", unique=True),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    # Unique identifier for this inventory record.

    variant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
    )
    # Identifier of the product variant (cross-domain reference, no FK).

    quantity_on_hand: Mapped[int] = mapped_column(Integer, nullable=False)
    # Physical stock available in the warehouse.

    quantity_reserved: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # Units currently reserved for open orders.

    movements: Mapped[list[StockMovement]] = relationship(
        "StockMovement",
        back_populates="inventory_item",
        cascade="all, delete-orphan",
    )
    # Append-only audit trail of stock movements.

    reservations: Mapped[list[Reservation]] = relationship(
        "Reservation",
        back_populates="inventory_item",
        cascade="all, delete-orphan",
    )
    # Active and historical reservations for this variant.

    @property
    def quantity_available(self) -> int:
        """Units available to reserve: on_hand minus already reserved."""
        return self.quantity_on_hand - self.quantity_reserved


class StockMovement(TimestampMixin, BaseModel):
    """Append-only audit trail entry for a stock change."""

    __tablename__ = "inventory_movements"

    __table_args__ = (
        Index("idx_inventory_movements_item_id", "inventory_item_id"),
        Index("idx_inventory_movements_reference_id", "reference_id"),
        CheckConstraint(
            "kind IN ('adjustment', 'reservation', 'release', 'confirmation')",
            name="ck_inventory_movements_kind",
        ),
        CheckConstraint("delta != 0", name="ck_inventory_movements_non_zero_delta"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    # Unique identifier for this movement record.

    inventory_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("inventory_items.id", name="fk_inventory_movements_item_id"),
        nullable=False,
    )
    # Identifier of the inventory item this movement belongs to.

    kind: Mapped[str] = mapped_column(String(20), nullable=False)
    # Type of movement — must be a MovementKind value.

    delta: Mapped[int] = mapped_column(Integer, nullable=False)
    # Signed quantity change for this movement.

    reference_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
    )
    # Optional external reference such as a reservation ID.

    note: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # Optional human-readable explanation for the movement.

    inventory_item: Mapped[InventoryItem] = relationship(
        "InventoryItem", back_populates="movements"
    )
    # The inventory item this movement belongs to.


class Reservation(TimestampMixin, BaseModel):
    """A stock reservation linking an inventory item to an order."""

    __tablename__ = "inventory_reservations"

    __table_args__ = (
        Index("idx_inventory_reservations_item_id", "inventory_item_id"),
        Index("idx_inventory_reservations_order_id", "order_id"),
        CheckConstraint(
            "quantity > 0", name="ck_inventory_reservations_positive_quantity"
        ),
        CheckConstraint(
            "status IN ('reserved', 'confirmed', 'released')",
            name="ck_inventory_reservations_status",
        ),
        UniqueConstraint(
            "inventory_item_id", "order_id", name="uq_inventory_reservations_item_order"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    # Unique identifier for this reservation.

    inventory_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("inventory_items.id", name="fk_inventory_reservations_item_id"),
        nullable=False,
    )
    # Identifier of the inventory item being reserved.

    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
    )
    # Identifier of the order requesting the reservation (cross-domain ref, no FK).

    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    # Quantity reserved for the order.

    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=ReservationStatus.RESERVED
    )
    # Reservation lifecycle status — must be a ReservationStatus value.

    inventory_item: Mapped[InventoryItem] = relationship(
        "InventoryItem", back_populates="reservations"
    )
    # The inventory item this reservation belongs to.
