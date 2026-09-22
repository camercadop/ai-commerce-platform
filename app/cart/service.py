import logging
import uuid
from decimal import Decimal
from typing import Literal

from app.cart.events import (
    publish_cart_cleared,
    publish_cart_created,
    publish_cart_item_added,
    publish_cart_item_removed,
    publish_cart_item_updated,
    publish_cart_merged,
    publish_cart_updated,
)
from app.cart.exceptions import (
    CartItemNotFound,
    CartNotFound,
    InvalidCartStatus,
    InventoryUnavailable,
    MergeConflict,
    VariantNotFound,
)
from app.cart.models import Cart, CartItem
from app.cart.ports import CatalogPort, InventoryPort
from app.cart.repository import CartItemRepository, CartRepository
from app.shared.audit_log import AuditPort, FieldChange, record_audit
from app.shared.events import MessageBroker

logger = logging.getLogger(__name__)


class CartService:
    """Manages cart lifecycle and cart item mutations."""

    def __init__(
        self,
        cart_repo: CartRepository,
        cart_item_repo: CartItemRepository,
        catalog_port: CatalogPort,
        inventory_port: InventoryPort,
        audit: AuditPort,
        broker: MessageBroker,
    ) -> None:
        self.cart_repo = cart_repo
        self.cart_item_repo = cart_item_repo
        self._catalog = catalog_port
        self._inventory = inventory_port
        self._audit = audit
        self._broker = broker

    def _require_active_cart(self, cart_id: uuid.UUID) -> Cart:
        """Load a cart by id and enforce that it exists and is active.

        Raises:
            CartNotFound: If no active cart exists for the id.
            InvalidCartStatus: If the cart is not in active status.
        """
        cart = self.cart_repo.get_with_items(cart_id)
        if cart is None:
            raise CartNotFound(cart_id)
        if cart.status != "active":
            raise InvalidCartStatus(f"Cart is not active: {cart.status}")
        return cart

    def _require_variant(self, variant_id: uuid.UUID, quantity: int) -> Decimal:
        """Validate catalog availability and inventory for a variant.

        Args:
            variant_id: UUID of the product variant.
            quantity: Requested quantity.

        Returns:
            The current catalog price.

        Raises:
            VariantNotFound: If the variant cannot be found in the catalog.
            InventoryUnavailable: If inventory is insufficient for the
                requested quantity.
        """
        price = self._catalog.get_variant_price(variant_id)
        if price is None:
            raise VariantNotFound(variant_id)
        if not self._inventory.check_availability(variant_id, quantity):
            raise InventoryUnavailable(
                f"Variant {variant_id} is unavailable for quantity {quantity}"
            )
        return price

    def _claim_simple(
        self,
        cart: Cart,
        customer_id: uuid.UUID,
        actor_id: uuid.UUID | None = None,
    ) -> None:
        """Bind an anonymous cart to a customer without merging."""
        cart.customer_id = customer_id
        self.cart_repo.session.flush()
        logger.info("Cart claimed by customer: %s", cart.id)
        publish_cart_updated(
            self._broker,
            cart.id,
            mutation="cart_claimed",
            items_count=len(cart.items),
        )
        if actor_id is not None:
            record_audit(
                self._audit,
                actor_id=actor_id,
                operation="update",
                action="cart.cart_claimed",
                aggregate_type="cart",
                aggregate_id=cart.id,
                domain="cart",
                changes={
                    "customer_id": FieldChange(before=None, after=str(customer_id)),
                },
            )

    def _after_mutation(
        self,
        cart_id: uuid.UUID,
        mutation: str,
        items_count: int,
        actor_id: uuid.UUID | None,
        operation: Literal["create", "update", "delete"],
        action: str,
        changes: dict[str, FieldChange] | None,
    ) -> None:
        """Publish CartUpdated and record audit for a completed mutation."""
        publish_cart_updated(
            self._broker,
            cart_id,
            mutation=mutation,
            items_count=items_count,
        )
        if actor_id is not None:
            record_audit(
                self._audit,
                actor_id=actor_id,
                operation=operation,
                action=action,
                aggregate_type="cart",
                aggregate_id=cart_id,
                domain="cart",
                changes=changes,
            )

    def _merge_item(self, customer_cart: Cart, anon_item: CartItem) -> int:
        """Merge one anonymous cart item into the customer cart.

        Returns:
            1 if a new item was created, 0 if an existing item was updated.
        """
        existing = self.cart_item_repo.get_by_cart_and_variant(
            customer_cart.id, anon_item.variant_id
        )
        price = self._catalog.get_variant_price(anon_item.variant_id)
        if price is None:
            raise MergeConflict(
                f"Variant {anon_item.variant_id} not found in catalog during merge"
            )
        if existing is not None:
            new_quantity = existing.quantity + anon_item.quantity
            if not self._inventory.check_availability(
                anon_item.variant_id, new_quantity
            ):
                raise MergeConflict(
                    f"Insufficient inventory for variant {anon_item.variant_id}"
                )
            existing.quantity = new_quantity
            existing.unit_price = price
            self.cart_item_repo.session.flush()
            return 0
        if not self._inventory.check_availability(
            anon_item.variant_id, anon_item.quantity
        ):
            raise MergeConflict(
                f"Insufficient inventory for variant {anon_item.variant_id}"
            )
        new_item = CartItem(
            cart_id=customer_cart.id,
            variant_id=anon_item.variant_id,
            quantity=anon_item.quantity,
            unit_price=price,
            discount_value=anon_item.discount_value,
            discount_percent=anon_item.discount_percent,
            tax_value=anon_item.tax_value,
            tax_percent=anon_item.tax_percent,
        )
        self.cart_item_repo.session.add(new_item)
        customer_cart.items.append(new_item)
        self.cart_item_repo.session.flush()
        return 1

    def create_cart(
        self,
        session_id: str,
        customer_id: uuid.UUID | None = None,
        actor_id: uuid.UUID | None = None,
    ) -> Cart:
        """Create a new cart for the given session, returning an existing one if
        present.

        get_or_create_by_session_id is idempotent for anonymous carts. If the
        caller passes customer_id and the returned cart is still unclaimed,
        this method performs a simple bind — no merge. For merge semantics,
        use claim_cart instead.

        Args:
            session_id: Client-supplied session token.
            customer_id: Optional authenticated customer id to bind.
            actor_id: UUID of the actor performing the operation, or None.

        Returns:
            The existing or newly created Cart instance.
        """
        cart, created = self.cart_repo.get_or_create_by_session_id(session_id)
        if created:
            publish_cart_created(
                self._broker,
                cart.id,
                session_id=session_id,
                customer_id=customer_id,
            )
        if customer_id is not None and cart.customer_id is None:
            self._claim_simple(cart, customer_id, actor_id)
        return cart

    def claim_cart(
        self,
        session_id: str,
        customer_id: uuid.UUID,
        actor_id: uuid.UUID | None = None,
    ) -> Cart:
        """Claim an anonymous cart for a customer.

        Idempotent: if the cart is already claimed by the same customer, no-op.
        If the customer already has an active cart, merge the anonymous cart into
        the customer cart and soft-delete the anonymous cart.

        Args:
            session_id: Client-supplied session token.
            customer_id: UUID of the authenticated customer.
            actor_id: UUID of the actor performing the operation, or None.

        Returns:
            The customer's cart after merging.

        Raises:
            CartNotFound: If no active cart exists for the session.
            MergeConflict: If the customer already has a cart and merge cannot proceed.
        """
        cart = self.cart_repo.get_by_session_id(session_id)
        if cart is None:
            raise CartNotFound(session_id)
        if cart.customer_id == customer_id:
            return cart
        customer_cart = self.cart_repo.get_by_customer_id(customer_id)
        if customer_cart is not None:
            self._merge_carts(customer_cart, cart, actor_id=actor_id)
            return customer_cart
        self._claim_simple(cart, customer_id, actor_id)
        return cart

    def _merge_carts(
        self,
        customer_cart: Cart,
        anonymous_cart: Cart,
        actor_id: uuid.UUID | None = None,
    ) -> None:
        """Merge items from an anonymous cart into the customer's cart.

        Quantities are summed. Unit prices are re-read from the catalog.
        Inventory is checked per merged quantity. The anonymous cart is then
        soft-deleted.

        Args:
            customer_cart: The target authenticated cart.
            anonymous_cart: The source anonymous cart to merge from.
            actor_id: UUID of the actor performing the operation, or None.

        Raises:
            MergeConflict: If a merge conflict cannot be resolved.
        """
        merged_count = sum(
            self._merge_item(customer_cart, anon_item)
            for anon_item in list(anonymous_cart.items)
        )
        anonymous_cart.soft_delete()
        self.cart_repo.session.flush()
        logger.info(
            "Merged anonymous cart %s into customer cart %s",
            anonymous_cart.id,
            customer_cart.id,
        )
        publish_cart_merged(
            self._broker,
            customer_cart.id,
            source_session_id=anonymous_cart.session_id,
            merged_count=merged_count,
        )
        self._after_mutation(
            cart_id=customer_cart.id,
            mutation="cart_merged",
            items_count=len(customer_cart.items),
            actor_id=actor_id,
            operation="update",
            action="cart.cart_merged",
            changes={
                "merged_from": FieldChange(before=None, after=str(anonymous_cart.id)),
                "merged_count": FieldChange(before=None, after=merged_count),
            },
        )

    def add_cart_item(
        self,
        cart_id: uuid.UUID,
        variant_id: uuid.UUID,
        quantity: int,
        actor_id: uuid.UUID | None = None,
    ) -> CartItem:
        """Add a variant to the cart, merging with existing line item if present.

        Args:
            cart_id: UUID of the cart.
            variant_id: UUID of the product variant.
            quantity: Quantity to add.
            actor_id: UUID of the actor performing the operation, or None.

        Returns:
            The created or updated CartItem instance.

        Raises:
            CartNotFound: If the cart does not exist or is soft-deleted.
            InvalidCartStatus: If the cart is not in active status.
            VariantNotFound: If the variant cannot be found in the catalog.
            InventoryUnavailable: If inventory is insufficient for the
                requested quantity.
        """
        cart = self._require_active_cart(cart_id)
        price = self._require_variant(variant_id, quantity)

        existing = self.cart_item_repo.get_by_cart_and_variant(cart_id, variant_id)
        operation: Literal["create", "update", "delete"]
        if existing is not None:
            existing.quantity += quantity
            existing.unit_price = price
            self.cart_item_repo.session.flush()
            item = existing
            mutation = "item_updated"
            operation = "update"
            action = "cart.item_updated"
        else:
            item = CartItem(
                cart_id=cart_id,
                variant_id=variant_id,
                quantity=quantity,
                unit_price=price,
                discount_value=Decimal("0"),
                discount_percent=Decimal("0"),
                tax_value=Decimal("0"),
                tax_percent=Decimal("0"),
            )
            self.cart_item_repo.session.add(item)
            self.cart_item_repo.session.flush()
            mutation = "item_added"
            operation = "create"
            action = "cart.item_added"
        logger.info("Cart item %s: %s", mutation, item.id)
        publish_cart_item_added(
            self._broker,
            cart_id,
            item.id,
            variant_id,
            {"quantity": item.quantity, "unit_price": str(item.unit_price)},
        )
        self._after_mutation(
            cart_id=cart_id,
            mutation=mutation,
            items_count=len(cart.items),
            actor_id=actor_id,
            operation=operation,
            action=action,
            changes={
                "variant_id": FieldChange(before=None, after=str(variant_id)),
                "quantity": FieldChange(
                    before=None if mutation == "item_added" else 0,
                    after=item.quantity,
                ),
                "unit_price": FieldChange(
                    before=None if mutation == "item_added" else Decimal("0"),
                    after=item.unit_price,
                ),
            },
        )
        return item

    def update_cart_item(
        self,
        cart_id: uuid.UUID,
        item_id: uuid.UUID,
        quantity: int,
        actor_id: uuid.UUID | None = None,
    ) -> CartItem:
        """Set the exact quantity for a cart item, re-reading the current catalog price.

        Args:
            cart_id: UUID of the cart.
            item_id: UUID of the cart item.
            quantity: New quantity for the item.
            actor_id: UUID of the actor performing the operation, or None.

        Returns:
            The updated CartItem instance.

        Raises:
            CartNotFound: If the cart does not exist or is soft-deleted.
            InvalidCartStatus: If the cart is not in active status.
            CartItemNotFound: If the cart item does not exist.
            VariantNotFound: If the variant cannot be found in the catalog.
            InventoryUnavailable: If inventory is insufficient for the
                requested quantity.
        """
        cart = self._require_active_cart(cart_id)
        item = next((i for i in cart.items if i.id == item_id), None)
        if item is None:
            raise CartItemNotFound(item_id)
        price = self._require_variant(item.variant_id, quantity)

        item.quantity = quantity
        item.unit_price = price
        self.cart_item_repo.session.flush()
        logger.info("Cart item updated: %s", item.id)
        publish_cart_item_updated(
            self._broker,
            cart_id,
            item.id,
            item.variant_id,
            {"quantity": item.quantity, "unit_price": str(item.unit_price)},
        )
        self._after_mutation(
            cart_id=cart_id,
            mutation="item_updated",
            items_count=len(cart.items),
            actor_id=actor_id,
            operation="update",
            action="cart.item_updated",
            changes={
                "quantity": FieldChange(before=item.quantity, after=item.quantity),
                "unit_price": FieldChange(
                    before=item.unit_price, after=item.unit_price
                ),
            },
        )
        return item

    def remove_cart_item(
        self,
        cart_id: uuid.UUID,
        item_id: uuid.UUID,
        actor_id: uuid.UUID | None = None,
    ) -> None:
        """Remove a cart item permanently.

        Args:
            cart_id: UUID of the cart.
            item_id: UUID of the cart item.
            actor_id: UUID of the actor performing the operation, or None.

        Raises:
            CartNotFound: If the cart does not exist or is soft-deleted.
            InvalidCartStatus: If the cart is not in active status.
            CartItemNotFound: If the cart item does not exist.
        """
        cart = self._require_active_cart(cart_id)
        item = next((i for i in cart.items if i.id == item_id), None)
        if item is None:
            raise CartItemNotFound(item_id)
        self.cart_item_repo.session.delete(item)
        self.cart_item_repo.session.flush()
        logger.info("Cart item removed: %s", item_id)
        publish_cart_item_removed(
            self._broker,
            cart_id,
            item_id,
            item.variant_id,
        )
        self._after_mutation(
            cart_id=cart_id,
            mutation="item_removed",
            items_count=len(cart.items),
            actor_id=actor_id,
            operation="delete",
            action="cart.item_removed",
            changes={
                "item_id": FieldChange(before=str(item_id), after=None),
                "variant_id": FieldChange(before=str(item.variant_id), after=None),
            },
        )

    def clear_cart(
        self,
        cart_id: uuid.UUID,
        actor_id: uuid.UUID | None = None,
    ) -> None:
        """Remove all items from the cart.

        Args:
            cart_id: UUID of the cart.
            actor_id: UUID of the actor performing the operation, or None.

        Raises:
            CartNotFound: If the cart does not exist or is soft-deleted.
            InvalidCartStatus: If the cart is not in active status.
        """
        cart = self._require_active_cart(cart_id)
        for item in list(cart.items):
            self.cart_item_repo.session.delete(item)
        self.cart_item_repo.session.flush()
        logger.info("Cart cleared: %s", cart_id)
        publish_cart_cleared(self._broker, cart_id)
        self._after_mutation(
            cart_id=cart_id,
            mutation="cart_cleared",
            items_count=0,
            actor_id=actor_id,
            operation="delete",
            action="cart.cart_cleared",
            changes=None,
        )

    def get_cart(self, cart_id: uuid.UUID) -> Cart:
        """Return the cart with items eagerly loaded.

        Args:
            cart_id: UUID of the cart.

        Returns:
            The Cart instance with items loaded.

        Raises:
            CartNotFound: If the cart does not exist or is soft-deleted.
        """
        cart = self.cart_repo.get_with_items(cart_id)
        if cart is None:
            raise CartNotFound(cart_id)
        return cart
