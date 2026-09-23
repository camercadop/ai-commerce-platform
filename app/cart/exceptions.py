from app.shared.exceptions import ResourceNotFound


class CartError(Exception):
    """Base exception for the cart domain.

    Catch this to handle any cart domain failure as a group.
    Prefer catching specific subclasses when the failure mode matters.
    """

    code = "CART_ERROR"


class CartNotFound(ResourceNotFound):
    """Raised when a cart does not exist or has been soft-deleted."""

    code = "CART_NOT_FOUND"
    resource_name = "Cart"


class CartItemNotFound(ResourceNotFound):
    """Raised when a cart item does not exist."""

    code = "CART_ITEM_NOT_FOUND"
    resource_name = "CartItem"


class InvalidCartStatus(CartError):
    """Raised when a cart is not in active status for a mutation operation."""

    code = "CART_INVALID_STATUS"


class InventoryUnavailable(CartError):
    """Raised when inventory check fails for a variant.

    Maps to 409 Conflict responses.
    """

    code = "CART_INVENTORY_UNAVAILABLE"
    status_code = 409


class VariantNotFound(ResourceNotFound):
    """Raised when a product variant cannot be found in the catalog."""

    code = "CART_VARIANT_NOT_FOUND"
    resource_name = "Variant"


class SessionCartConflict(CartError):
    """Raised when a session already has an active cart."""

    code = "CART_SESSION_CONFLICT"
    status_code = 409


class MergeConflict(CartError):
    """Raised when cart merge encounters an unresolvable conflict."""

    code = "CART_MERGE_CONFLICT"
    status_code = 409
