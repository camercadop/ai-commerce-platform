import pytest

from app.shared.storage import ObjectNotFound, ObjectStorage


class InMemoryObjectStorage(ObjectStorage):
    """In-memory implementation of ObjectStorage for use in tests."""

    def __init__(self) -> None:
        self._store: dict[str, tuple[bytes, str]] = {}

    def put(self, key: str, data: bytes, content_type: str) -> None:
        """Store an object in memory."""
        self._store[key] = (data, content_type)

    def get(self, key: str) -> bytes:
        """Return the stored bytes or raise ObjectNotFound."""
        if key not in self._store:
            raise ObjectNotFound(key)
        return self._store[key][0]

    def delete(self, key: str) -> None:
        """Remove the object if it exists, no-op otherwise."""
        self._store.pop(key, None)

    def exists(self, key: str) -> bool:
        """Return True if the key is present in the store."""
        return key in self._store


@pytest.fixture()
def storage() -> InMemoryObjectStorage:
    """Provide a fresh InMemoryObjectStorage for each test."""
    return InMemoryObjectStorage()


def test_put_and_get_object(storage: InMemoryObjectStorage) -> None:
    storage.put("products/abc/image.jpg", b"image-bytes", "image/jpeg")

    result = storage.get("products/abc/image.jpg")

    assert result == b"image-bytes"


def test_get_raises_object_not_found(storage: InMemoryObjectStorage) -> None:
    with pytest.raises(ObjectNotFound) as exc_info:
        storage.get("missing/key.jpg")

    assert exc_info.value.key == "missing/key.jpg"
    assert exc_info.value.code == "OBJECT_NOT_FOUND"


def test_exists_returns_true_after_put(storage: InMemoryObjectStorage) -> None:
    storage.put("products/abc/image.jpg", b"data", "image/jpeg")

    assert storage.exists("products/abc/image.jpg") is True


def test_exists_returns_false_for_missing_key(storage: InMemoryObjectStorage) -> None:
    assert storage.exists("missing/key.jpg") is False


def test_delete_removes_object(storage: InMemoryObjectStorage) -> None:
    storage.put("products/abc/image.jpg", b"data", "image/jpeg")
    storage.delete("products/abc/image.jpg")

    assert storage.exists("products/abc/image.jpg") is False


def test_delete_is_noop_for_missing_key(storage: InMemoryObjectStorage) -> None:
    storage.delete("missing/key.jpg")

    assert storage.exists("missing/key.jpg") is False


def test_put_overwrites_existing_object(storage: InMemoryObjectStorage) -> None:
    storage.put("products/abc/image.jpg", b"original", "image/jpeg")
    storage.put("products/abc/image.jpg", b"updated", "image/jpeg")

    assert storage.get("products/abc/image.jpg") == b"updated"
