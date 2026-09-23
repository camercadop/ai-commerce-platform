import logging
import uuid

from app.inventory.events import (
    publish_inventory_confirmed,
    publish_inventory_released,
    publish_inventory_reserved,
)
from app.inventory.exceptions import (
    InsufficientStock,
    InvalidReservationTransition,
    InventoryItemAlreadyExists,
    InventoryItemNotFound,
    ReservationNotFound,
)
from app.inventory.models import InventoryItem, Reservation, ReservationStatus
from app.inventory.repository import InventoryRepository, ReservationRepository
from app.shared.audit_log import FieldChange, record_audit
from app.shared.audit_log.port import AuditPort
from app.shared.events import MessageBroker

logger = logging.getLogger(__name__)


class InventoryService:
    """Manages inventory operations: creation, adjustment, and stock reservations."""

    def __init__(
        self,
        inventory_repo: InventoryRepository,
        reservation_repo: ReservationRepository,
        audit: AuditPort,
        broker: MessageBroker,
    ) -> None:
        self.inventory_repo = inventory_repo
        self.reservation_repo = reservation_repo
        self._audit = audit
        self._broker = broker

    def create_inventory_item(
        self,
        variant_id: uuid.UUID,
        initial_quantity: int,
        actor_id: uuid.UUID,
    ) -> InventoryItem:
        """Create a new inventory item with initial stock quantity.

        Raises:
            InventoryItemAlreadyExists: If an inventory item for the variant
            already exists.
        """
        if self.inventory_repo.get_by_variant(variant_id) is not None:
            raise InventoryItemAlreadyExists(variant_id)

        item = self.inventory_repo.create(
            variant_id=variant_id,
            quantity_on_hand=initial_quantity,
            quantity_reserved=0,
        )

        record_audit(
            self._audit,
            actor_id=actor_id,
            operation="create",
            action="inventory.item.create",
            aggregate_type="inventory_item",
            aggregate_id=item.id,
            domain="inventory",
            changes={
                "variant_id": FieldChange(before=None, after=str(variant_id)),
                "quantity_on_hand": FieldChange(before=None, after=initial_quantity),
                "quantity_reserved": FieldChange(before=None, after=0),
            },
        )

        logger.info("Inventory item created: %s", item.id)
        return item

    def adjust_stock(
        self,
        variant_id: uuid.UUID,
        delta: int,
        note: str | None,
        actor_id: uuid.UUID,
    ) -> InventoryItem:
        """Adjust stock quantity by the given delta.

        Raises:
            InventoryItemNotFound: If the inventory item does not exist.
            InsufficientStock: If the resulting quantity_on_hand would be negative.
        """
        item = self.inventory_repo.get_by_variant_for_update(variant_id)

        if item.quantity_on_hand + delta < 0:
            raise InsufficientStock(variant_id)

        item.quantity_on_hand += delta
        self.inventory_repo.session.flush()

        record_audit(
            self._audit,
            actor_id=actor_id,
            operation="update",
            action="inventory.item.adjust",
            aggregate_type="inventory_item",
            aggregate_id=item.id,
            domain="inventory",
            changes={
                "quantity_on_hand": FieldChange(
                    before=item.quantity_on_hand - delta, after=item.quantity_on_hand
                ),
                "note": FieldChange(before=None, after=note),
            },
        )

        logger.info("Stock adjusted: variant=%s, delta=%s", variant_id, delta)
        return item

    def reserve(
        self,
        variant_id: uuid.UUID,
        order_id: uuid.UUID,
        quantity: int,
        actor_id: uuid.UUID,
    ) -> Reservation:
        """Reserve stock for an order.

        Returns the existing reservation if one already exists for the order.

        Raises:
            InventoryItemNotFound: If the inventory item does not exist.
            InsufficientStock: If there is not enough available stock.
        """
        item = self.inventory_repo.get_by_variant_for_update(variant_id)

        existing = self.reservation_repo.get_by_order(order_id)
        for res in existing:
            if res.status == ReservationStatus.RESERVED:
                return res

        if item.quantity_available < quantity:
            raise InsufficientStock(variant_id)

        item.quantity_reserved += quantity
        self.inventory_repo.session.flush()

        reservation = self.reservation_repo.create(
            inventory_item_id=item.id,
            order_id=order_id,
            quantity=quantity,
            status=ReservationStatus.RESERVED,
        )

        publish_inventory_reserved(
            self._broker,
            reservation.id,
            variant_id,
            order_id,
            quantity,
        )

        record_audit(
            self._audit,
            actor_id=actor_id,
            operation="create",
            action="inventory.reservation.create",
            aggregate_type="reservation",
            aggregate_id=reservation.id,
            domain="inventory",
            changes={
                "inventory_item_id": FieldChange(before=None, after=str(item.id)),
                "order_id": FieldChange(before=None, after=str(order_id)),
                "quantity": FieldChange(before=None, after=quantity),
                "status": FieldChange(before=None, after=ReservationStatus.RESERVED),
            },
        )

        logger.info(
            "Stock reserved: variant=%s, order=%s, quantity=%s",
            variant_id,
            order_id,
            quantity,
        )
        return reservation

    def release_reservation(
        self,
        reservation_id: uuid.UUID,
        actor_id: uuid.UUID,
    ) -> Reservation:
        """Release a stock reservation.

        Returns the reservation unchanged if it is already released.

        Raises:
            ReservationNotFound: If the reservation does not exist.
            InvalidReservationTransition: If the reservation is confirmed.
        """
        reservation = self.reservation_repo.get_by_id(reservation_id)

        if reservation is None:
            raise ReservationNotFound(reservation_id)

        if reservation.status == ReservationStatus.RELEASED:
            return reservation

        if reservation.status == ReservationStatus.CONFIRMED:
            raise InvalidReservationTransition(reservation_id)

        item = self.inventory_repo.get_by_id_for_update(reservation.inventory_item_id)

        item.quantity_reserved -= reservation.quantity
        self.inventory_repo.session.flush()

        reservation.status = ReservationStatus.RELEASED
        self.reservation_repo.session.flush()

        publish_inventory_released(
            self._broker,
            reservation_id,
            reservation.inventory_item_id,
            reservation.order_id,
            reservation.quantity,
        )

        record_audit(
            self._audit,
            actor_id=actor_id,
            operation="update",
            action="inventory.reservation.release",
            aggregate_type="reservation",
            aggregate_id=reservation_id,
            domain="inventory",
            changes={
                "status": FieldChange(
                    before=ReservationStatus.RESERVED, after=ReservationStatus.RELEASED
                ),
            },
        )

        logger.info("Stock released: reservation=%s", reservation_id)
        return reservation

    def confirm_reservation(
        self,
        reservation_id: uuid.UUID,
        actor_id: uuid.UUID,
    ) -> Reservation:
        """Confirm a stock reservation (payment success).

        Returns the reservation unchanged if it is already confirmed.

        Raises:
            ReservationNotFound: If the reservation does not exist.
            InvalidReservationTransition: If the reservation is released.
        """
        reservation = self.reservation_repo.get_by_id(reservation_id)

        if reservation is None:
            raise ReservationNotFound(reservation_id)

        if reservation.status == ReservationStatus.CONFIRMED:
            return reservation

        if reservation.status == ReservationStatus.RELEASED:
            raise InvalidReservationTransition(reservation_id)

        item = self.inventory_repo.get_by_id_for_update(reservation.inventory_item_id)

        item.quantity_reserved -= reservation.quantity
        item.quantity_on_hand -= reservation.quantity
        self.inventory_repo.session.flush()

        reservation.status = ReservationStatus.CONFIRMED
        self.reservation_repo.session.flush()

        publish_inventory_confirmed(
            self._broker,
            reservation_id,
            reservation.inventory_item_id,
            reservation.order_id,
            reservation.quantity,
        )

        record_audit(
            self._audit,
            actor_id=actor_id,
            operation="update",
            action="inventory.reservation.confirm",
            aggregate_type="reservation",
            aggregate_id=reservation_id,
            domain="inventory",
            changes={
                "status": FieldChange(
                    before=ReservationStatus.RESERVED, after=ReservationStatus.CONFIRMED
                ),
            },
        )

        logger.info("Stock confirmed: reservation=%s", reservation_id)
        return reservation

    def get_inventory(self, variant_id: uuid.UUID) -> InventoryItem:
        """Get inventory item by variant identifier.

        Raises:
            InventoryItemNotFound: If the inventory item does not exist.
        """
        item = self.inventory_repo.get_by_variant(variant_id)

        if item is None:
            raise InventoryItemNotFound(variant_id)

        return item
