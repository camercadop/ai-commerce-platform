import uuid

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.orders.models import Order, OrderItem
from app.shared.db import BaseRepository


class OrderRepository(BaseRepository[Order]):
    """Repository for Order persistence operations.

    Provides lookup by customer and order-with-items eager loading.
    All queries exclude soft-deleted records.
    """

    model_class = Order

    def get_with_items(self, order_id: uuid.UUID) -> Order | None:
        """Return the order with its items eagerly loaded, or None.

        Args:
            order_id: The UUID of the order.
        """
        stmt = (
            select(Order)
            .where(Order.id == order_id)
            .options(selectinload(Order.items), selectinload(Order.adjustments))
        )
        return self.session.execute(stmt).scalar_one_or_none()

    def list_by_customer(self, customer_id: uuid.UUID) -> list[Order]:
        """Return all orders belonging to the given customer.

        Args:
            customer_id: The UUID of the customer.
        """
        stmt = (
            select(Order)
            .where(Order.customer_id == customer_id)
            .order_by(Order.created_at.desc())
        )
        return list(self.session.execute(stmt).scalars().all())


class OrderItemRepository(BaseRepository[OrderItem]):
    """Repository for OrderItem persistence operations.

    Order items are hard-deleted when removed.
    """

    model_class = OrderItem

    def list_by_order(self, order_id: uuid.UUID) -> list[OrderItem]:
        """Return all items belonging to the given order.

        Args:
            order_id: The UUID of the order.
        """
        stmt = (
            select(OrderItem)
            .where(OrderItem.order_id == order_id)
            .order_by(OrderItem.created_at)
        )
        return list(self.session.execute(stmt).scalars().all())
