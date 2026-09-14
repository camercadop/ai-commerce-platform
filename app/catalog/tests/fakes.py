import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.exc import IntegrityError

from app.catalog.models import Brand, Category, CategoryAttribute, Product, Variant
from app.shared.audit_log import AuditPort, AuditRecord
from app.shared.events import EventEnvelope, MessageBroker


def make_category(**kwargs: Any) -> Category:
    """Build a Category instance with sensible defaults for testing."""
    obj = Category()
    obj.id = kwargs.get("id", uuid.uuid4())  # type: ignore[assignment]
    obj.name = kwargs.get("name", "Electronics")  # type: ignore[assignment]
    obj.description = kwargs.get("description", None)  # type: ignore[assignment]
    obj.parent_id = kwargs.get("parent_id", None)  # type: ignore[assignment]
    obj.deleted_at = kwargs.get("deleted_at", None)  # type: ignore[assignment]
    obj.created_at = kwargs.get("created_at", datetime.now(UTC))  # type: ignore[assignment]
    obj.updated_at = kwargs.get("updated_at", datetime.now(UTC))  # type: ignore[assignment]
    obj.attributes = kwargs.get("attributes", [])  # type: ignore[assignment]
    return obj


def make_brand(**kwargs: Any) -> Brand:
    """Build a Brand instance with sensible defaults for testing."""
    obj = Brand()
    obj.id = kwargs.get("id", uuid.uuid4())  # type: ignore[assignment]
    obj.name = kwargs.get("name", "Acme")  # type: ignore[assignment]
    obj.website = kwargs.get("website", None)  # type: ignore[assignment]
    obj.contact_email = kwargs.get("contact_email", None)  # type: ignore[assignment]
    obj.description = kwargs.get("description", None)  # type: ignore[assignment]
    obj.deleted_at = kwargs.get("deleted_at", None)  # type: ignore[assignment]
    obj.created_at = kwargs.get("created_at", datetime.now(UTC))  # type: ignore[assignment]
    obj.updated_at = kwargs.get("updated_at", datetime.now(UTC))  # type: ignore[assignment]
    return obj


def make_product(**kwargs: Any) -> Product:
    """Build a Product instance with sensible defaults for testing."""
    obj = Product()
    obj.id = kwargs.get("id", uuid.uuid4())  # type: ignore[assignment]
    obj.sku = kwargs.get("sku", "SKU-001")  # type: ignore[assignment]
    obj.name = kwargs.get("name", "Widget")  # type: ignore[assignment]
    obj.description = kwargs.get("description", None)  # type: ignore[assignment]
    obj.category_id = kwargs.get("category_id", None)  # type: ignore[assignment]
    obj.brand_id = kwargs.get("brand_id", None)  # type: ignore[assignment]
    obj.base_price = kwargs.get("base_price", "9.99")  # type: ignore[assignment]
    obj.status = kwargs.get("status", "draft")  # type: ignore[assignment]
    obj.specs = kwargs.get("specs", None)  # type: ignore[assignment]
    obj.deleted_at = kwargs.get("deleted_at", None)  # type: ignore[assignment]
    obj.created_at = kwargs.get("created_at", datetime.now(UTC))  # type: ignore[assignment]
    obj.updated_at = kwargs.get("updated_at", datetime.now(UTC))  # type: ignore[assignment]
    return obj


def make_variant(**kwargs: Any) -> Variant:
    """Build a Variant instance with sensible defaults for testing."""
    obj = Variant()
    obj.id = kwargs.get("id", uuid.uuid4())  # type: ignore[assignment]
    obj.product_id = kwargs.get("product_id", uuid.uuid4())  # type: ignore[assignment]
    obj.sku = kwargs.get("sku", "VAR-001")  # type: ignore[assignment]
    obj.price = kwargs.get("price", "9.99")  # type: ignore[assignment]
    obj.attributes = kwargs.get("attributes", {})  # type: ignore[assignment]
    obj.deleted_at = kwargs.get("deleted_at", None)  # type: ignore[assignment]
    obj.created_at = kwargs.get("created_at", datetime.now(UTC))  # type: ignore[assignment]
    obj.updated_at = kwargs.get("updated_at", datetime.now(UTC))  # type: ignore[assignment]
    return obj


def make_category_attribute(**kwargs: Any) -> CategoryAttribute:
    """Build a CategoryAttribute instance with sensible defaults for testing."""
    obj = CategoryAttribute()
    obj.id = kwargs.get("id", uuid.uuid4())  # type: ignore[assignment]
    obj.category_id = kwargs.get("category_id", uuid.uuid4())  # type: ignore[assignment]
    obj.key = kwargs.get("key", "color")  # type: ignore[assignment]
    obj.value_type = kwargs.get("value_type", "string")  # type: ignore[assignment]
    obj.required = kwargs.get("required", False)  # type: ignore[assignment]
    obj.deleted_at = kwargs.get("deleted_at", None)  # type: ignore[assignment]
    obj.created_at = kwargs.get("created_at", datetime.now(UTC))  # type: ignore[assignment]
    obj.updated_at = kwargs.get("updated_at", datetime.now(UTC))  # type: ignore[assignment]
    return obj


class FakeAuditPort(AuditPort):
    """In-memory AuditPort for unit tests."""

    def __init__(self) -> None:
        self.recorded: list[AuditRecord] = []

    def record(self, entry: AuditRecord) -> None:
        """Capture the audit record for assertion."""
        self.recorded.append(entry)


class FakeCategoryRepository:
    """In-memory CategoryRepository for unit tests."""

    def __init__(self, categories: list[Category] | None = None) -> None:
        self._store: dict[uuid.UUID, Category] = {c.id: c for c in (categories or [])}

    def get_by_id(self, record_id: uuid.UUID) -> Category | None:
        """Return the active category with the given id, or None."""
        c = self._store.get(record_id)
        return c if c and c.deleted_at is None else None

    def get_by_name(
        self, name: str, parent_id: uuid.UUID | None = None
    ) -> Category | None:
        """Return the active category matching name and parent, or None."""
        return next(
            (
                c
                for c in self._store.values()
                if c.name.lower() == name.lower()
                and c.parent_id == parent_id
                and c.deleted_at is None
            ),
            None,
        )

    def list_root(self, limit: int, cursor: Any = None) -> list[Category]:
        """Return active root categories."""
        return [
            c
            for c in self._store.values()
            if c.parent_id is None and c.deleted_at is None
        ][:limit]

    def list_by_parent(
        self, parent_id: uuid.UUID, limit: int, cursor: Any = None
    ) -> list[Category]:
        """Return active child categories under the given parent."""
        return [
            c
            for c in self._store.values()
            if c.parent_id == parent_id and c.deleted_at is None
        ][:limit]

    def create(self, **kwargs: Any) -> Category:
        """Create and store a new category."""
        obj = make_category(**kwargs)
        self._store[obj.id] = obj
        return obj

    def update(self, record: Category, data: dict[str, Any]) -> Category:
        """Apply a partial update to the given category."""
        for k, v in data.items():
            setattr(record, k, v)
        return record

    def delete(self, record: Category) -> None:
        """Soft-delete the given category."""
        record.deleted_at = datetime.now(UTC)


class FakeBrandRepository:
    """In-memory BrandRepository for unit tests."""

    def __init__(self, brands: list[Brand] | None = None) -> None:
        self._store: dict[uuid.UUID, Brand] = {b.id: b for b in (brands or [])}

    def get_by_id(self, record_id: uuid.UUID) -> Brand | None:
        """Return the active brand with the given id, or None."""
        b = self._store.get(record_id)
        return b if b and b.deleted_at is None else None

    def get_by_name(self, name: str) -> Brand | None:
        """Return the active brand matching the given name, or None."""
        return next(
            (
                b
                for b in self._store.values()
                if b.name == name and b.deleted_at is None
            ),
            None,
        )

    def create(self, **kwargs: Any) -> Brand:
        """Create and store a new brand."""
        obj = make_brand(**kwargs)
        self._store[obj.id] = obj
        return obj

    def update(self, record: Brand, data: dict[str, Any]) -> Brand:
        """Apply a partial update to the given brand."""
        for k, v in data.items():
            setattr(record, k, v)
        return record

    def delete(self, record: Brand) -> None:
        """Soft-delete the given brand."""
        record.deleted_at = datetime.now(UTC)


class FakeProductRepository:
    """In-memory ProductRepository for unit tests."""

    def __init__(self, products: list[Product] | None = None) -> None:
        self._store: dict[uuid.UUID, Product] = {p.id: p for p in (products or [])}

    def get_by_id(self, record_id: uuid.UUID) -> Product | None:
        """Return the active product with the given id, or None."""
        p = self._store.get(record_id)
        return p if p and p.deleted_at is None else None

    def get_by_sku(self, sku: str) -> Product | None:
        """Return the active product matching the given SKU, or None."""
        return next(
            (p for p in self._store.values() if p.sku == sku and p.deleted_at is None),
            None,
        )

    def list_by_category(
        self, category_id: uuid.UUID, limit: int, cursor: Any = None
    ) -> list[Product]:
        """Return active products in the given category."""
        return [
            p
            for p in self._store.values()
            if p.category_id == category_id and p.deleted_at is None
        ][:limit]

    def list_by_brand(
        self, brand_id: uuid.UUID, limit: int, cursor: Any = None
    ) -> list[Product]:
        """Return active products for the given brand."""
        return [
            p
            for p in self._store.values()
            if p.brand_id == brand_id and p.deleted_at is None
        ][:limit]

    def create(self, **kwargs: Any) -> Product:
        """Create and store a new product."""
        obj = make_product(**kwargs)
        self._store[obj.id] = obj
        return obj

    def update(self, record: Product, data: dict[str, Any]) -> Product:
        """Apply a partial update to the given product."""
        for k, v in data.items():
            setattr(record, k, v)
        return record

    def delete(self, record: Product) -> None:
        """Soft-delete the given product."""
        record.deleted_at = datetime.now(UTC)


class FakeVariantRepository:
    """In-memory VariantRepository for unit tests."""

    def __init__(self, variants: list[Variant] | None = None) -> None:
        self._store: dict[uuid.UUID, Variant] = {v.id: v for v in (variants or [])}

    def get_by_id(self, record_id: uuid.UUID) -> Variant | None:
        """Return the active variant with the given id, or None."""
        v = self._store.get(record_id)
        return v if v and v.deleted_at is None else None

    def get_by_sku(self, sku: str) -> Variant | None:
        """Return the active variant matching the given SKU, or None."""
        return next(
            (v for v in self._store.values() if v.sku == sku and v.deleted_at is None),
            None,
        )

    def list_by_product(
        self, product_id: uuid.UUID, limit: int, cursor: Any = None
    ) -> list[Variant]:
        """Return active variants for the given product."""
        return [
            v
            for v in self._store.values()
            if v.product_id == product_id and v.deleted_at is None
        ][:limit]

    def create(self, **kwargs: Any) -> Variant:
        """Create and store a new variant."""
        obj = make_variant(**kwargs)
        self._store[obj.id] = obj
        return obj

    def update(self, record: Variant, data: dict[str, Any]) -> Variant:
        """Apply a partial update to the given variant."""
        for k, v in data.items():
            setattr(record, k, v)
        return record

    def delete(self, record: Variant) -> None:
        """Soft-delete the given variant."""
        record.deleted_at = datetime.now(UTC)


class RaisingMessageBroker(MessageBroker):
    """Message broker that always raises on publish."""

    def publish(self, topic: str, envelope: EventEnvelope) -> None:
        raise RuntimeError("broker unavailable")

    def subscribe(self, topic: str, handler: Any) -> None:  # type: ignore[override]
        pass


class _IntegrityErrorOnWrite:
    """Mixin that raises IntegrityError on create and update."""

    def _raise(self) -> None:
        raise IntegrityError(None, None, Exception("unique constraint"))

    def create(self, **kwargs: Any) -> Any:  # type: ignore[override]
        self._raise()

    def update(self, record: Any, data: Any) -> Any:  # type: ignore[override]
        self._raise()


class IntegrityErrorCategoryRepository(_IntegrityErrorOnWrite, FakeCategoryRepository):
    pass


class IntegrityErrorBrandRepository(_IntegrityErrorOnWrite, FakeBrandRepository):
    pass


class IntegrityErrorProductRepository(_IntegrityErrorOnWrite, FakeProductRepository):
    pass


class IntegrityErrorVariantRepository(_IntegrityErrorOnWrite, FakeVariantRepository):
    pass


class FakeCategoryAttributeRepository:
    """In-memory CategoryAttributeRepository for unit tests."""

    def __init__(self, attributes: list[CategoryAttribute] | None = None) -> None:
        self._store: dict[uuid.UUID, CategoryAttribute] = {
            a.id: a for a in (attributes or [])
        }

    def get_by_id(self, record_id: uuid.UUID) -> CategoryAttribute | None:
        """Return the attribute with the given id, or None."""
        return self._store.get(record_id)

    def get_by_category_and_key(
        self, category_id: uuid.UUID, key: str
    ) -> CategoryAttribute | None:
        """Return the attribute matching category and key, or None."""
        return next(
            (
                a
                for a in self._store.values()
                if a.category_id == category_id and a.key == key
            ),
            None,
        )

    def list_by_category(
        self, category_id: uuid.UUID, limit: int, cursor: Any = None
    ) -> list[CategoryAttribute]:
        """Return attribute definitions for the given category."""
        return [a for a in self._store.values() if a.category_id == category_id][:limit]

    def create(self, **kwargs: Any) -> CategoryAttribute:
        """Create and store a new category attribute."""
        obj = make_category_attribute(**kwargs)
        self._store[obj.id] = obj
        return obj

    def update(
        self, record: CategoryAttribute, data: dict[str, Any]
    ) -> CategoryAttribute:
        """Apply a partial update to the given attribute."""
        for k, v in data.items():
            setattr(record, k, v)
        return record

    def delete(self, record: CategoryAttribute) -> None:
        """Hard-delete the given attribute."""
        self._store.pop(record.id, None)


class IntegrityErrorAttributeRepository(
    _IntegrityErrorOnWrite, FakeCategoryAttributeRepository
):
    pass
