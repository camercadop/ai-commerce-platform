import uuid

import pytest

from app.inventory.exceptions import (
    InsufficientStock,
    InvalidReservationTransition,
    InventoryItemAlreadyExists,
    InventoryItemNotFound,
    ReservationNotFound,
)
from app.inventory.models import ReservationStatus
from app.inventory.service import InventoryService
from app.inventory.tests.fakes import (
    FakeAuditPort,
    FakeInventoryRepository,
    FakeReservationRepository,
    RaisingMessageBroker,
    make_inventory_item,
    make_reservation,
)
from app.shared.events import NoOpMessageBroker

_ACTOR = uuid.UUID(int=0)


def _inventory_service(
    items: list | None = None,
    reservations: list | None = None,
    audit: FakeAuditPort | None = None,
    broker: MessageBroker | None = None,
) -> tuple[InventoryService, FakeAuditPort]:
    audit_port = audit or FakeAuditPort()
    svc = InventoryService(
        inventory_repo=FakeInventoryRepository(items),
        reservation_repo=FakeReservationRepository(reservations),
        audit=audit_port,
        broker=broker or NoOpMessageBroker(),
    )
    return svc, audit_port


# ---------------------------------------------------------------------------
# InventoryService.create_inventory_item
# ---------------------------------------------------------------------------


class TestInventoryServiceCreateInventoryItem:
    def test_creates_item_with_initial_quantity(self) -> None:
        variant_id = uuid.uuid4()
        svc, _ = _inventory_service()

        item = svc.create_inventory_item(
            variant_id=variant_id, initial_quantity=10, actor_id=_ACTOR
        )

        assert item.variant_id == variant_id
        assert item.quantity_on_hand == 10
        assert item.quantity_reserved == 0

    def test_raises_if_already_exists(self) -> None:
        variant_id = uuid.uuid4()
        existing = make_inventory_item(variant_id=variant_id, quantity_on_hand=5)
        svc, _ = _inventory_service(items=[existing])

        with pytest.raises(InventoryItemAlreadyExists):
            svc.create_inventory_item(
                variant_id=variant_id, initial_quantity=10, actor_id=_ACTOR
            )

    def test_records_audit(self) -> None:
        variant_id = uuid.uuid4()
        svc, audit = _inventory_service()

        svc.create_inventory_item(
            variant_id=variant_id, initial_quantity=10, actor_id=_ACTOR
        )

        assert len(audit.recorded) == 1
        record = audit.recorded[0]
        assert record.action == "inventory.item.create"
        assert record.domain == "inventory"


# ---------------------------------------------------------------------------
# InventoryService.adjust_stock
# ---------------------------------------------------------------------------


class TestInventoryServiceAdjustStock:
    def test_adjusts_stock_positive_delta(self) -> None:
        variant_id = uuid.uuid4()
        item = make_inventory_item(variant_id=variant_id, quantity_on_hand=10)
        svc, _ = _inventory_service(items=[item])

        result = svc.adjust_stock(
            variant_id=variant_id, delta=5, note="restock", actor_id=_ACTOR
        )

        assert result.quantity_on_hand == 15

    def test_adjusts_stock_negative_delta(self) -> None:
        variant_id = uuid.uuid4()
        item = make_inventory_item(variant_id=variant_id, quantity_on_hand=10)
        svc, _ = _inventory_service(items=[item])

        result = svc.adjust_stock(
            variant_id=variant_id, delta=-3, note="shrinkage", actor_id=_ACTOR
        )

        assert result.quantity_on_hand == 7

    def test_raises_if_item_not_found(self) -> None:
        svc, _ = _inventory_service()

        with pytest.raises(InventoryItemNotFound):
            svc.adjust_stock(
                variant_id=uuid.uuid4(), delta=5, note="restock", actor_id=_ACTOR
            )

    def test_raises_if_result_would_be_negative(self) -> None:
        variant_id = uuid.uuid4()
        item = make_inventory_item(variant_id=variant_id, quantity_on_hand=5)
        svc, _ = _inventory_service(items=[item])

        with pytest.raises(InsufficientStock):
            svc.adjust_stock(
                variant_id=variant_id, delta=-10, note="shrinkage", actor_id=_ACTOR
            )

    def test_records_audit(self) -> None:
        variant_id = uuid.uuid4()
        item = make_inventory_item(variant_id=variant_id, quantity_on_hand=10)
        svc, audit = _inventory_service(items=[item])

        svc.adjust_stock(
            variant_id=variant_id, delta=5, note="restock", actor_id=_ACTOR
        )

        assert len(audit.recorded) == 1
        record = audit.recorded[0]
        assert record.action == "inventory.item.adjust"
        assert record.domain == "inventory"


# ---------------------------------------------------------------------------
# InventoryService.reserve
# ---------------------------------------------------------------------------


class TestInventoryServiceReserve:
    def test_reserves_stock_successfully(self) -> None:
        variant_id = uuid.uuid4()
        order_id = uuid.uuid4()
        item = make_inventory_item(variant_id=variant_id, quantity_on_hand=10)
        svc, _ = _inventory_service(items=[item])

        reservation = svc.reserve(
            variant_id=variant_id, order_id=order_id, quantity=3, actor_id=_ACTOR
        )

        assert reservation.inventory_item_id == item.id
        assert reservation.order_id == order_id
        assert reservation.quantity == 3
        assert reservation.status == ReservationStatus.RESERVED
        assert item.quantity_reserved == 3

    def test_returns_existing_reservation_when_already_reserved(self) -> None:
        variant_id = uuid.uuid4()
        order_id = uuid.uuid4()
        item = make_inventory_item(variant_id=variant_id, quantity_on_hand=10)
        existing = make_reservation(
            inventory_item_id=item.id, order_id=order_id, quantity=2
        )
        svc, _ = _inventory_service(items=[item], reservations=[existing])

        result = svc.reserve(
            variant_id=variant_id, order_id=order_id, quantity=2, actor_id=_ACTOR
        )

        assert result.id == existing.id

    def test_raises_if_item_not_found(self) -> None:
        svc, _ = _inventory_service()

        with pytest.raises(InventoryItemNotFound):
            svc.reserve(
                variant_id=uuid.uuid4(),
                order_id=uuid.uuid4(),
                quantity=1,
                actor_id=_ACTOR,
            )

    def test_raises_if_insufficient_stock(self) -> None:
        variant_id = uuid.uuid4()
        order_id = uuid.uuid4()
        item = make_inventory_item(variant_id=variant_id, quantity_on_hand=2)
        svc, _ = _inventory_service(items=[item])

        with pytest.raises(InsufficientStock):
            svc.reserve(
                variant_id=variant_id, order_id=order_id, quantity=5, actor_id=_ACTOR
            )

    def test_broker_failure_does_not_raise(self) -> None:
        variant_id = uuid.uuid4()
        order_id = uuid.uuid4()
        item = make_inventory_item(variant_id=variant_id, quantity_on_hand=10)
        broker = RaisingMessageBroker()
        svc, _ = _inventory_service(items=[item], broker=broker)

        reservation = svc.reserve(
            variant_id=variant_id, order_id=order_id, quantity=3, actor_id=_ACTOR
        )

        assert reservation is not None

    def test_records_audit(self) -> None:
        variant_id = uuid.uuid4()
        order_id = uuid.uuid4()
        item = make_inventory_item(variant_id=variant_id, quantity_on_hand=10)
        svc, audit = _inventory_service(items=[item])

        svc.reserve(
            variant_id=variant_id, order_id=order_id, quantity=3, actor_id=_ACTOR
        )

        assert len(audit.recorded) == 1
        record = audit.recorded[0]
        assert record.action == "inventory.reservation.create"
        assert record.domain == "inventory"


# ---------------------------------------------------------------------------
# InventoryService.release_reservation
# ---------------------------------------------------------------------------


class TestInventoryServiceReleaseReservation:
    def test_releases_reservation_successfully(self) -> None:
        item = make_inventory_item(quantity_on_hand=10, quantity_reserved=5)
        reservation = make_reservation(
            inventory_item_id=item.id, quantity=3, status=ReservationStatus.RESERVED
        )
        svc, _ = _inventory_service(items=[item], reservations=[reservation])

        result = svc.release_reservation(
            reservation_id=reservation.id, actor_id=_ACTOR
        )

        assert result.status == ReservationStatus.RELEASED
        assert item.quantity_reserved == 2

    def test_returns_unchanged_if_already_released(self) -> None:
        item = make_inventory_item(quantity_on_hand=10, quantity_reserved=5)
        reservation = make_reservation(
            inventory_item_id=item.id, quantity=3, status=ReservationStatus.RELEASED
        )
        svc, _ = _inventory_service(items=[item], reservations=[reservation])

        result = svc.release_reservation(
            reservation_id=reservation.id, actor_id=_ACTOR
        )

        assert result.status == ReservationStatus.RELEASED
        assert item.quantity_reserved == 5

    def test_raises_if_not_found(self) -> None:
        svc, _ = _inventory_service()

        with pytest.raises(ReservationNotFound):
            svc.release_reservation(
                reservation_id=uuid.uuid4(), actor_id=_ACTOR
            )

    def test_raises_if_confirmed(self) -> None:
        item = make_inventory_item(quantity_on_hand=10, quantity_reserved=5)
        reservation = make_reservation(
            inventory_item_id=item.id, quantity=3, status=ReservationStatus.CONFIRMED
        )
        svc, _ = _inventory_service(items=[item], reservations=[reservation])

        with pytest.raises(InvalidReservationTransition):
            svc.release_reservation(
                reservation_id=reservation.id, actor_id=_ACTOR
            )

    def test_broker_failure_does_not_raise(self) -> None:
        item = make_inventory_item(quantity_on_hand=10, quantity_reserved=5)
        reservation = make_reservation(
            inventory_item_id=item.id, quantity=3, status=ReservationStatus.RESERVED
        )
        broker = RaisingMessageBroker()
        svc, _ = _inventory_service(
            items=[item], reservations=[reservation], broker=broker
        )

        result = svc.release_reservation(
            reservation_id=reservation.id, actor_id=_ACTOR
        )

        assert result.status == ReservationStatus.RELEASED

    def test_records_audit(self) -> None:
        item = make_inventory_item(quantity_on_hand=10, quantity_reserved=5)
        reservation = make_reservation(
            inventory_item_id=item.id, quantity=3, status=ReservationStatus.RESERVED
        )
        svc, audit = _inventory_service(items=[item], reservations=[reservation])

        svc.release_reservation(
            reservation_id=reservation.id, actor_id=_ACTOR
        )

        assert len(audit.recorded) == 1
        record = audit.recorded[0]
        assert record.action == "inventory.reservation.release"
        assert record.domain == "inventory"


# ---------------------------------------------------------------------------
# InventoryService.confirm_reservation
# ---------------------------------------------------------------------------


class TestInventoryServiceConfirmReservation:
    def test_confirms_reservation_successfully(self) -> None:
        item = make_inventory_item(quantity_on_hand=10, quantity_reserved=5)
        reservation = make_reservation(
            inventory_item_id=item.id, quantity=3, status=ReservationStatus.RESERVED
        )
        svc, _ = _inventory_service(items=[item], reservations=[reservation])

        result = svc.confirm_reservation(
            reservation_id=reservation.id, actor_id=_ACTOR
        )

        assert result.status == ReservationStatus.CONFIRMED
        assert item.quantity_reserved == 2
        assert item.quantity_on_hand == 7

    def test_returns_unchanged_if_already_confirmed(self) -> None:
        item = make_inventory_item(quantity_on_hand=10, quantity_reserved=5)
        reservation = make_reservation(
            inventory_item_id=item.id, quantity=3, status=ReservationStatus.CONFIRMED
        )
        svc, _ = _inventory_service(items=[item], reservations=[reservation])

        result = svc.confirm_reservation(
            reservation_id=reservation.id, actor_id=_ACTOR
        )

        assert result.status == ReservationStatus.CONFIRMED
        assert item.quantity_reserved == 5
        assert item.quantity_on_hand == 10

    def test_raises_if_not_found(self) -> None:
        svc, _ = _inventory_service()

        with pytest.raises(ReservationNotFound):
            svc.confirm_reservation(
                reservation_id=uuid.uuid4(), actor_id=_ACTOR
            )

    def test_raises_if_released(self) -> None:
        item = make_inventory_item(quantity_on_hand=10, quantity_reserved=5)
        reservation = make_reservation(
            inventory_item_id=item.id, quantity=3, status=ReservationStatus.RELEASED
        )
        svc, _ = _inventory_service(items=[item], reservations=[reservation])

        with pytest.raises(InvalidReservationTransition):
            svc.confirm_reservation(
                reservation_id=reservation.id, actor_id=_ACTOR
            )

    def test_broker_failure_does_not_raise(self) -> None:
        item = make_inventory_item(quantity_on_hand=10, quantity_reserved=5)
        reservation = make_reservation(
            inventory_item_id=item.id, quantity=3, status=ReservationStatus.RESERVED
        )
        broker = RaisingMessageBroker()
        svc, _ = _inventory_service(
            items=[item], reservations=[reservation], broker=broker
        )

        result = svc.confirm_reservation(
            reservation_id=reservation.id, actor_id=_ACTOR
        )

        assert result.status == ReservationStatus.CONFIRMED

    def test_records_audit(self) -> None:
        item = make_inventory_item(quantity_on_hand=10, quantity_reserved=5)
        reservation = make_reservation(
            inventory_item_id=item.id, quantity=3, status=ReservationStatus.RESERVED
        )
        svc, audit = _inventory_service(items=[item], reservations=[reservation])

        svc.confirm_reservation(
            reservation_id=reservation.id, actor_id=_ACTOR
        )

        assert len(audit.recorded) == 1
        record = audit.recorded[0]
        assert record.action == "inventory.reservation.confirm"
        assert record.domain == "inventory"


# ---------------------------------------------------------------------------
# InventoryService.get_inventory
# ---------------------------------------------------------------------------


class TestInventoryServiceGetInventory:
    def test_returns_item(self) -> None:
        variant_id = uuid.uuid4()
        item = make_inventory_item(variant_id=variant_id)
        svc, _ = _inventory_service(items=[item])

        result = svc.get_inventory(variant_id)

        assert result.id == item.id

    def test_raises_if_not_found(self) -> None:
        svc, _ = _inventory_service()

        with pytest.raises(InventoryItemNotFound):
            svc.get_inventory(uuid.uuid4())
