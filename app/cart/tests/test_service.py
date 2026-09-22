import uuid

import pytest
from decimal import Decimal

from app.cart.exceptions import (
    CartItemNotFound,
    CartNotFound,
    InvalidCartStatus,
    InventoryUnavailable,
    MergeConflict,
    VariantNotFound,
)
from app.cart.models import Cart, CartItem
from app.cart.service import CartService
from app.cart.tests.fakes import (
    FakeAuditPort,
    FakeCartItemRepository,
    FakeCartRepository,
    FakeCatalogPort,
    FakeInventoryPort,
    RaisingMessageBroker,
    make_cart,
    make_cart_item,
)
from app.shared.events import MessageBroker, NoOpMessageBroker


def _cart_service(
    carts: list[Cart] | None = None,
    items: list[CartItem] | None = None,
    catalog_prices: dict[uuid.UUID, Decimal] | None = None,
    inventory_available: dict[uuid.UUID, bool] | None = None,
    audit: FakeAuditPort | None = None,
    broker: MessageBroker | None = None,
) -> CartService:
    return CartService(
        cart_repo=FakeCartRepository(carts),
        cart_item_repo=FakeCartItemRepository(items),
        catalog_port=FakeCatalogPort(catalog_prices),
        inventory_port=FakeInventoryPort(inventory_available),
        audit=audit or FakeAuditPort(),
        broker=broker or NoOpMessageBroker(),
    )


# ---------------------------------------------------------------------------
# CartService.create_cart
# ---------------------------------------------------------------------------


class TestCartServiceCreateCart:
    def test_creates_new_cart(self) -> None:
        svc = _cart_service()

        cart = svc.create_cart(session_id="s1")

        assert cart.session_id == "s1"
        assert cart.customer_id is None
        assert cart.status == "active"

    def test_returns_existing_cart_for_same_session(self) -> None:
        existing = make_cart(session_id="s1")
        svc = _cart_service(carts=[existing])

        cart = svc.create_cart(session_id="s1")

        assert cart.id == existing.id

    def test_claims_cart_when_customer_id_provided(self) -> None:
        cart = make_cart(session_id="s1")
        customer_id = uuid.uuid4()
        svc = _cart_service(carts=[cart])

        result = svc.create_cart(session_id="s1", customer_id=customer_id)

        assert result.customer_id == customer_id


# ---------------------------------------------------------------------------
# CartService.claim_cart
# ---------------------------------------------------------------------------


class TestCartServiceClaimCart:
    def test_raises_if_cart_not_found(self) -> None:
        svc = _cart_service()

        with pytest.raises(CartNotFound):
            svc.claim_cart(session_id="missing", customer_id=uuid.uuid4())

    def test_is_idempotent_when_already_claimed_by_same_customer(self) -> None:
        customer_id = uuid.uuid4()
        cart = make_cart(session_id="s1", customer_id=customer_id)
        svc = _cart_service(carts=[cart])

        result = svc.claim_cart(session_id="s1", customer_id=customer_id)

        assert result.id == cart.id

    def test_claims_simple_when_customer_has_no_cart(self) -> None:
        cart = make_cart(session_id="s1")
        customer_id = uuid.uuid4()
        svc = _cart_service(carts=[cart])

        result = svc.claim_cart(session_id="s1", customer_id=customer_id)

        assert result.customer_id == customer_id

    def test_merges_when_customer_has_existing_cart(self) -> None:
        customer_id = uuid.uuid4()
        variant_id = uuid.uuid4()
        customer_cart = make_cart(session_id="s2", customer_id=customer_id)
        anon_cart = make_cart(session_id="s1")
        anon_item = make_cart_item(cart_id=anon_cart.id, variant_id=variant_id, quantity=2)
        anon_cart.items.append(anon_item)
        svc = _cart_service(
            carts=[customer_cart, anon_cart],
            items=[anon_item],
            catalog_prices={variant_id: Decimal("5.00")},
            inventory_available={variant_id: True},
        )

        result = svc.claim_cart(session_id="s1", customer_id=customer_id)

        assert result.id == customer_cart.id
        assert anon_cart.deleted_at is not None
        assert len(result.items) == 1
        assert result.items[0].quantity == 2
        assert result.items[0].unit_price == Decimal("5.00")

    def test_merge_raises_when_variant_missing_from_catalog(self) -> None:
        customer_id = uuid.uuid4()
        variant_id = uuid.uuid4()
        customer_cart = make_cart(session_id="s2", customer_id=customer_id)
        anon_cart = make_cart(session_id="s1")
        anon_item = make_cart_item(cart_id=anon_cart.id, variant_id=variant_id, quantity=1)
        anon_cart.items.append(anon_item)
        svc = _cart_service(
            carts=[customer_cart, anon_cart],
            items=[anon_item],
            catalog_prices={},
        )

        with pytest.raises(MergeConflict):
            svc.claim_cart(session_id="s1", customer_id=customer_id)

    def test_merge_raises_when_inventory_insufficient(self) -> None:
        customer_id = uuid.uuid4()
        variant_id = uuid.uuid4()
        customer_cart = make_cart(session_id="s2", customer_id=customer_id)
        anon_cart = make_cart(session_id="s1")
        anon_item = make_cart_item(cart_id=anon_cart.id, variant_id=variant_id, quantity=5)
        anon_cart.items.append(anon_item)
        svc = _cart_service(
            carts=[customer_cart, anon_cart],
            items=[anon_item],
            catalog_prices={variant_id: Decimal("5.00")},
            inventory_available={variant_id: False},
        )

        with pytest.raises(MergeConflict):
            svc.claim_cart(session_id="s1", customer_id=customer_id)


# ---------------------------------------------------------------------------
# CartService.add_cart_item
# ---------------------------------------------------------------------------


class TestCartServiceAddCartItem:
    def test_raises_if_cart_not_found(self) -> None:
        svc = _cart_service()

        with pytest.raises(CartNotFound):
            svc.add_cart_item(cart_id=uuid.uuid4(), variant_id=uuid.uuid4(), quantity=1)

    def test_raises_if_cart_not_active(self) -> None:
        cart = make_cart(status="checked_out")
        svc = _cart_service(carts=[cart])

        with pytest.raises(InvalidCartStatus):
            svc.add_cart_item(cart_id=cart.id, variant_id=uuid.uuid4(), quantity=1)

    def test_raises_if_variant_not_found(self) -> None:
        cart = make_cart()
        svc = _cart_service(carts=[cart])

        with pytest.raises(VariantNotFound):
            svc.add_cart_item(cart_id=cart.id, variant_id=uuid.uuid4(), quantity=1)

    def test_raises_if_inventory_unavailable(self) -> None:
        variant_id = uuid.uuid4()
        cart = make_cart()
        svc = _cart_service(
            carts=[cart],
            catalog_prices={variant_id: Decimal("9.99")},
            inventory_available={variant_id: False},
        )

        with pytest.raises(InventoryUnavailable):
            svc.add_cart_item(cart_id=cart.id, variant_id=variant_id, quantity=1)

    def test_adds_new_item(self) -> None:
        variant_id = uuid.uuid4()
        cart = make_cart()
        svc = _cart_service(
            carts=[cart],
            catalog_prices={variant_id: Decimal("9.99")},
            inventory_available={variant_id: True},
        )

        item = svc.add_cart_item(cart_id=cart.id, variant_id=variant_id, quantity=2)

        assert item.variant_id == variant_id
        assert item.quantity == 2
        assert item.unit_price == Decimal("9.99")

    def test_updates_existing_item_quantity_and_price(self) -> None:
        variant_id = uuid.uuid4()
        cart = make_cart()
        existing = make_cart_item(cart_id=cart.id, variant_id=variant_id, quantity=1)
        cart.items.append(existing)
        svc = _cart_service(
            carts=[cart],
            items=[existing],
            catalog_prices={variant_id: Decimal("4.99")},
            inventory_available={variant_id: True},
        )

        item = svc.add_cart_item(cart_id=cart.id, variant_id=variant_id, quantity=3)

        assert item.quantity == 4
        assert item.unit_price == Decimal("4.99")


# ---------------------------------------------------------------------------
# CartService.update_cart_item
# ---------------------------------------------------------------------------


class TestCartServiceUpdateCartItem:
    def test_raises_if_cart_not_found(self) -> None:
        svc = _cart_service()

        with pytest.raises(CartNotFound):
            svc.update_cart_item(
                cart_id=uuid.uuid4(), item_id=uuid.uuid4(), quantity=1
            )

    def test_raises_if_cart_not_active(self) -> None:
        cart = make_cart(status="checked_out")
        svc = _cart_service(carts=[cart])

        with pytest.raises(InvalidCartStatus):
            svc.update_cart_item(cart_id=cart.id, item_id=uuid.uuid4(), quantity=1)

    def test_raises_if_item_not_found(self) -> None:
        cart = make_cart()
        svc = _cart_service(carts=[cart])

        with pytest.raises(CartItemNotFound):
            svc.update_cart_item(cart_id=cart.id, item_id=uuid.uuid4(), quantity=1)

    def test_raises_if_variant_not_found(self) -> None:
        variant_id = uuid.uuid4()
        cart = make_cart()
        item = make_cart_item(cart_id=cart.id, variant_id=variant_id)
        cart.items.append(item)
        svc = _cart_service(carts=[cart], items=[item])

        with pytest.raises(VariantNotFound):
            svc.update_cart_item(cart_id=cart.id, item_id=item.id, quantity=1)

    def test_raises_if_inventory_unavailable(self) -> None:
        variant_id = uuid.uuid4()
        cart = make_cart()
        item = make_cart_item(cart_id=cart.id, variant_id=variant_id)
        cart.items.append(item)
        svc = _cart_service(
            carts=[cart],
            items=[item],
            catalog_prices={variant_id: Decimal("9.99")},
            inventory_available={variant_id: False},
        )

        with pytest.raises(InventoryUnavailable):
            svc.update_cart_item(cart_id=cart.id, item_id=item.id, quantity=1)

    def test_updates_quantity_and_price(self) -> None:
        variant_id = uuid.uuid4()
        cart = make_cart()
        item = make_cart_item(cart_id=cart.id, variant_id=variant_id, quantity=1)
        cart.items.append(item)
        svc = _cart_service(
            carts=[cart],
            items=[item],
            catalog_prices={variant_id: Decimal("4.99")},
            inventory_available={variant_id: True},
        )

        result = svc.update_cart_item(cart_id=cart.id, item_id=item.id, quantity=5)

        assert result.quantity == 5
        assert result.unit_price == Decimal("4.99")


# ---------------------------------------------------------------------------
# CartService.remove_cart_item
# ---------------------------------------------------------------------------


class TestCartServiceRemoveCartItem:
    def test_raises_if_cart_not_found(self) -> None:
        svc = _cart_service()

        with pytest.raises(CartNotFound):
            svc.remove_cart_item(cart_id=uuid.uuid4(), item_id=uuid.uuid4())

    def test_raises_if_cart_not_active(self) -> None:
        cart = make_cart(status="checked_out")
        svc = _cart_service(carts=[cart])

        with pytest.raises(InvalidCartStatus):
            svc.remove_cart_item(cart_id=cart.id, item_id=uuid.uuid4())

    def test_raises_if_item_not_found(self) -> None:
        cart = make_cart()
        svc = _cart_service(carts=[cart])

        with pytest.raises(CartItemNotFound):
            svc.remove_cart_item(cart_id=cart.id, item_id=uuid.uuid4())

    def test_removes_item(self) -> None:
        variant_id = uuid.uuid4()
        cart = make_cart()
        item = make_cart_item(cart_id=cart.id, variant_id=variant_id)
        cart.items.append(item)
        svc = _cart_service(carts=[cart], items=[item])

        svc.remove_cart_item(cart_id=cart.id, item_id=item.id)

        assert svc.cart_item_repo.get_by_cart_and_variant(cart.id, variant_id) is None


# ---------------------------------------------------------------------------
# CartService.clear_cart
# ---------------------------------------------------------------------------


class TestCartServiceClearCart:
    def test_raises_if_cart_not_found(self) -> None:
        svc = _cart_service()

        with pytest.raises(CartNotFound):
            svc.clear_cart(cart_id=uuid.uuid4())

    def test_raises_if_cart_not_active(self) -> None:
        cart = make_cart(status="checked_out")
        svc = _cart_service(carts=[cart])

        with pytest.raises(InvalidCartStatus):
            svc.clear_cart(cart_id=cart.id)

    def test_clears_items(self) -> None:
        variant_id = uuid.uuid4()
        cart = make_cart()
        item = make_cart_item(cart_id=cart.id, variant_id=variant_id)
        cart.items.append(item)
        svc = _cart_service(carts=[cart], items=[item])

        svc.clear_cart(cart_id=cart.id)

        assert svc.cart_item_repo.get_by_cart_and_variant(cart.id, variant_id) is None


# ---------------------------------------------------------------------------
# CartService.get_cart
# ---------------------------------------------------------------------------


class TestCartServiceGetCart:
    def test_returns_cart_with_items(self) -> None:
        variant_id = uuid.uuid4()
        cart = make_cart()
        item = make_cart_item(cart_id=cart.id, variant_id=variant_id)
        cart.items.append(item)
        svc = _cart_service(carts=[cart], items=[item])

        result = svc.get_cart(cart.id)

        assert result.id == cart.id
        assert len(result.items) == 1

    def test_raises_if_cart_not_found(self) -> None:
        svc = _cart_service()

        with pytest.raises(CartNotFound):
            svc.get_cart(uuid.uuid4())
