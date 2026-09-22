import uuid

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from app.cart.models import Cart, CartItem
from app.shared.db import BaseRepository


class CartRepository(BaseRepository[Cart]):
    """Repository for Cart persistence operations.

    Provides lookup by session and customer in addition to the base CRUD
    interface. All queries exclude soft-deleted records.
    """

    model_class = Cart

    def get_by_session_id(self, session_id: str) -> Cart | None:
        """Return the active cart matching the given session_id, or None.

        Args:
            session_id: The client-supplied session token.
        """
        stmt = (
            select(Cart)
            .where(Cart.session_id == session_id)
            .where(Cart.deleted_at.is_(None))
        )
        return self.session.execute(stmt).scalar_one_or_none()

    def get_by_customer_id(self, customer_id: uuid.UUID) -> Cart | None:
        """Return the active cart belonging to the given customer, or None.

        Args:
            customer_id: The UUID of the customer.
        """
        stmt = (
            select(Cart)
            .where(Cart.customer_id == customer_id)
            .where(Cart.deleted_at.is_(None))
        )
        return self.session.execute(stmt).scalar_one_or_none()

    def get_with_items(self, cart_id: uuid.UUID) -> Cart | None:
        """Return the cart with its items eagerly loaded, or None.

        Args:
            cart_id: The UUID of the cart.
        """
        stmt = (
            select(Cart)
            .where(Cart.id == cart_id)
            .where(Cart.deleted_at.is_(None))
            .options(selectinload(Cart.items))
        )
        return self.session.execute(stmt).scalar_one_or_none()

    def get_or_create_by_session_id(self, session_id: str) -> tuple[Cart, bool]:
        """Return the active cart for the session, creating one if none exists.

        Uses an optimistic-insert strategy to handle concurrent requests: attempts
        to create first and falls back to a lookup on unique constraint violation.
        This is idempotent: calling it multiple times with the same session_id
        returns the same cart.

        Args:
            session_id: The client-supplied session token.

        Returns:
            A tuple of (cart, created) where created is True if the cart was
            newly created, False if an existing cart was returned.
        """
        cart = self.get_by_session_id(session_id)
        if cart is not None:
            return cart, False
        try:
            return self.create(session_id=session_id), True
        except IntegrityError:
            self.session.rollback()
            return self.get_by_session_id(session_id), True  # type: ignore[return-value]


class CartItemRepository(BaseRepository[CartItem]):
    """Repository for CartItem persistence operations.

    Cart items are hard-deleted on removal (no soft delete).
    """

    model_class = CartItem

    def get_by_cart_and_variant(
        self, cart_id: uuid.UUID, variant_id: uuid.UUID
    ) -> CartItem | None:
        """Return the cart item matching the given cart and variant, or None.

        Args:
            cart_id: The UUID of the cart.
            variant_id: The UUID of the product variant.
        """
        stmt = (
            select(CartItem)
            .where(CartItem.cart_id == cart_id)
            .where(CartItem.variant_id == variant_id)
        )
        return self.session.execute(stmt).scalar_one_or_none()

    def list_by_cart(self, cart_id: uuid.UUID) -> list[CartItem]:
        """Return all items belonging to the given cart.

        Args:
            cart_id: The UUID of the cart.
        """
        stmt = select(CartItem).where(CartItem.cart_id == cart_id)
        return list(self.session.execute(stmt).scalars().all())
