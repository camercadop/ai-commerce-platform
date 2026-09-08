import logging
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class ObjectStorage(ABC):
    """Abstract port for object storage operations.

    All concrete implementations must live in the domain module that requires
    them (e.g. app/media/). Domain code must never depend on a concrete
    storage implementation directly (ADR-004).

    Implementations are responsible for translating between this interface
    and the underlying provider (MinIO, S3, GCS, etc.). No provider-specific
    SDK or data format may appear in domain code.
    """

    @abstractmethod
    def put(self, key: str, data: bytes, content_type: str) -> None:
        """Store an object at the given key.

        Overwrites any existing object at the same key. The key is an opaque
        path string — callers are responsible for key namespacing conventions.

        Args:
            key: The storage key (e.g. "products/abc-123/image.jpg").
            data: The raw bytes to store.
            content_type: MIME type of the object (e.g. "image/jpeg").
        """

    @abstractmethod
    def get(self, key: str) -> bytes:
        """Retrieve the object stored at the given key.

        Args:
            key: The storage key of the object to retrieve.

        Returns:
            The raw bytes of the stored object.

        Raises:
            ObjectNotFound: If no object exists at the given key.
        """

    @abstractmethod
    def delete(self, key: str) -> None:
        """Delete the object at the given key.

        No-op if the object does not exist — callers must not rely on this
        raising an error for missing keys.

        Args:
            key: The storage key of the object to delete.
        """

    @abstractmethod
    def exists(self, key: str) -> bool:
        """Return True if an object exists at the given key, False otherwise.

        Args:
            key: The storage key to check.
        """
