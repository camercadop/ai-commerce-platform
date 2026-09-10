from app.shared.exceptions import ResourceAlreadyExists, ResourceNotFound


class IdentityError(Exception):
    """Base exception for the identity domain.

    Catch this to handle any identity domain failure as a group.
    Prefer catching specific subclasses when the failure mode matters.
    """

    code = "IDENTITY_ERROR"


class CustomerNotFound(ResourceNotFound):
    """Raised when a customer does not exist or has been soft-deleted."""

    code = "CUSTOMER_NOT_FOUND"
    resource_name = "Customer"


class CustomerAlreadyExists(ResourceAlreadyExists):
    """Raised when registering a customer whose identity_provider_id is already taken.

    The conflicting identifier is the identity_provider_id value.
    """

    code = "CUSTOMER_ALREADY_EXISTS"
    resource_name = "Customer"


class AddressNotFound(ResourceNotFound):
    """Raised when an address does not exist or has been soft-deleted."""

    code = "ADDRESS_NOT_FOUND"
    resource_name = "Address"


class InvalidPreferenceKey(Exception):
    """Raised when a preference key is not in the allowed list.

    The disallowed_keys attribute holds the set of keys that triggered the error.
    """

    code = "INVALID_PREFERENCE_KEY"

    def __init__(self, disallowed_keys: set[str]) -> None:
        self.disallowed_keys = disallowed_keys
        super().__init__(
            f"Invalid preference keys: {', '.join(sorted(disallowed_keys))}"
        )
