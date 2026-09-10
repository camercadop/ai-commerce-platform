class ResourceNotFound(Exception):
    """Raised when a requested resource does not exist.

    Domain exceptions should subclass this and set resource_name to the
    human-readable entity name (e.g. "Customer", "Product"). The code
    attribute is used by exception handlers to produce a consistent error
    response body.
    """

    code = "NOT_FOUND"
    resource_name = "Resource"

    def __init__(self, resource_id: object) -> None:
        self.resource_id = resource_id
        super().__init__(f"{self.resource_name} not found: {resource_id}")


class ResourceAlreadyExists(Exception):
    """Raised when attempting to create a resource that already exists.

    Domain exceptions should subclass this and set resource_name to the
    human-readable entity name. The identifier attribute holds the conflicting
    value that caused the uniqueness violation.
    """

    code = "ALREADY_EXISTS"
    resource_name = "Resource"

    def __init__(self, identifier: object) -> None:
        self.identifier = identifier
        super().__init__(f"{self.resource_name} already exists: {identifier}")
