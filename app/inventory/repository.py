import uuid

from sqlalchemy import select

from app.shared.db.repository import BaseRepository

from .exceptions import InventoryItemNotFound
from .models import InventoryItem, Reservation


class InventoryRepository(BaseRepository[InventoryItem]):
    """Repository for InventoryItem operations."""

    model_class = InventoryItem

    def get_by_variant(self, variant_id: uuid.UUID) -> InventoryItem | None:
        """Find an inventory item by variant identifier.

        Args:
            variant_id: The product variant identifier.

        Returns:
            The matching InventoryItem, or None if not found.
        """
        return self.find_one_by(variant_id=variant_id)

    def get_by_variant_for_update(self, variant_id: uuid.UUID) -> InventoryItem:
        """Find an inventory item by variant identifier with a write lock.

        Raises InventoryItemNotFound if the item does not exist.

        Args:
            variant_id: The product variant identifier.

        Returns:
            The matching InventoryItem with an exclusive row lock.
        """
        result = self.session.execute(
            select(self.model_class)
            .filter_by(variant_id=variant_id)
            .with_for_update(skip_locked=True)
        )
        item = result.scalar_one_or_none()
        if item is None:
            raise InventoryItemNotFound(variant_id)
        return item

    def get_by_id_for_update(self, record_id: uuid.UUID) -> InventoryItem:
        """Find an inventory item by primary key with a write lock.

        Raises InventoryItemNotFound if the item does not exist.

        Args:
            record_id: The inventory item primary key.

        Returns:
            The matching InventoryItem with an exclusive row lock.
        """
        result = self.session.execute(
            select(self.model_class)
            .filter_by(id=record_id)
            .with_for_update(skip_locked=True)
        )
        item = result.scalar_one_or_none()
        if item is None:
            raise InventoryItemNotFound(record_id)
        return item


class ReservationRepository(BaseRepository[Reservation]):
    """Repository for Reservation operations."""

    model_class = Reservation

    def get_by_order(self, order_id: uuid.UUID) -> list[Reservation]:
        """List all reservations for an order.

        Args:
            order_id: The order identifier.

        Returns:
            All reservations for the specified order.
        """
        return self.find_many_by(order_id=order_id)
