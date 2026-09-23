from app.shared.exceptions import ResourceAlreadyExists, ResourceNotFound


class InventoryError(Exception):
    """Base exception for the inventory domain.

    Catch this to handle any inventory domain failure as a group.
    Prefer catching specific subclasses when the failure mode matters.
    """

    code = "INVENTORY_ERROR"
    status_code = 400


class InventoryItemNotFound(ResourceNotFound):
    """Raised when an inventory item does not exist."""

    code = "INVENTORY_ITEM_NOT_FOUND"
    resource_name = "InventoryItem"


class InventoryItemAlreadyExists(ResourceAlreadyExists):
    """Raised when attempting to create an inventory item that already exists."""

    code = "INVENTORY_ITEM_ALREADY_EXISTS"
    resource_name = "InventoryItem"


class InsufficientStock(InventoryError):
    """Raised when there is not enough stock to fulfill a request."""

    code = "INVENTORY_INSUFFICIENT_STOCK"


class ReservationNotFound(ResourceNotFound):
    """Raised when a reservation does not exist."""

    code = "INVENTORY_RESERVATION_NOT_FOUND"
    resource_name = "Reservation"


class InvalidReservationTransition(InventoryError):
    """Raised when a reservation transition is not allowed."""

    code = "INVENTORY_INVALID_RESERVATION_TRANSITION"
