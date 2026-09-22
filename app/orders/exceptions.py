from app.shared.exceptions import ResourceNotFound


class OrderError(Exception):
    """Base exception for the orders domain.

    Catch this to handle any orders domain failure as a group.
    Prefer catching specific subclasses when the failure mode matters.
    """

    code = "ORDER_ERROR"
    status_code = 400


class OrderNotFound(ResourceNotFound):
    """Raised when an order does not exist."""

    code = "ORDER_NOT_FOUND"
    resource_name = "Order"


class InvalidCartReference(OrderError):
    """Raised when the cart port cannot resolve the given cart_id."""

    code = "ORDER_CART_INVALID_REFERENCE"


class CartNotEligibleForCheckout(OrderError):
    """Raised when the cart is not in active status and cannot be checked out."""

    code = "ORDER_CART_NOT_ELIGIBLE"


class CartHasNoItems(OrderError):
    """Raised when the cart has no items to check out."""

    code = "ORDER_CART_HAS_NO_ITEMS"
