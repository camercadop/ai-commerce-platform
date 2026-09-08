class ObjectNotFound(Exception):
    """Raised when a requested object does not exist in storage.

    Callers must handle this explicitly — never assume an object exists
    without checking first or catching this exception.
    """

    code = "OBJECT_NOT_FOUND"

    def __init__(self, key: str) -> None:
        self.key = key
        super().__init__(f"Object not found: {key}")
