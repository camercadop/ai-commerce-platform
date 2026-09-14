import logging
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.catalog.exceptions import (
    BrandAlreadyExists,
    BrandNotFound,
    CategoryAlreadyExists,
    CategoryAttributeAlreadyExists,
    CategoryAttributeNotFound,
    CategoryNotFound,
    InvalidVariantAttributes,
    ProductAlreadyExists,
    ProductNotFound,
    VariantAlreadyExists,
    VariantNotFound,
)
from app.catalog.models import Brand, Category, CategoryAttribute, Product, Variant
from app.catalog.repository import (
    BrandRepository,
    CategoryAttributeRepository,
    CategoryRepository,
    ProductRepository,
    VariantRepository,
)
from app.shared.audit_log import AuditPort, FieldChange, record_audit
from app.shared.events import EventEnvelope, MessageBroker

logger = logging.getLogger(__name__)

PAGE_SIZE = 20
_DOMAIN = "catalog"


def _publish(
    broker: MessageBroker,
    topic: str,
    event_type: str,
    aggregate_type: str,
    aggregate_id: uuid.UUID,
    data: dict[str, Any],
    trace_id: str,
) -> None:
    """Publish a domain event envelope to the broker.

    Best-effort: logs a warning on failure and never raises to the caller.

    Args:
        broker: The message broker port.
        topic: Broker topic in <domain>.<aggregate>.<event> format.
        event_type: PascalCase event name (e.g. ProductCreated).
        aggregate_type: The domain entity name (e.g. product).
        aggregate_id: UUID of the affected aggregate.
        data: Event payload dict.
        trace_id: Active OTel trace id for correlation.
    """
    try:
        broker.publish(
            topic,
            EventEnvelope(
                event_type=event_type,
                version=1,
                producer=_DOMAIN,
                aggregate_type=aggregate_type,
                aggregate_id=str(aggregate_id),
                trace_id=trace_id,
                data=data,
            ),
        )
    except Exception:
        logger.warning(
            "Failed to publish event %s for %s %s",
            event_type,
            aggregate_type,
            aggregate_id,
        )


class CategoryService:
    """Manages category creation, updates, and soft-deletion.

    All write operations flush within the service but do not commit —
    the caller (route handler) owns the transaction boundary.
    """

    def __init__(
        self, session: Session, audit: AuditPort, broker: MessageBroker
    ) -> None:
        """Initialize with an active session, audit port, and message broker.

        Args:
            session: The SQLAlchemy session scoped to the current request.
            audit: The audit port used to record state-changing operations.
            broker: The message broker port used to publish domain events.
        """
        self.repo = CategoryRepository(session)
        self._audit = audit
        self._broker = broker

    def create(
        self,
        actor_id: uuid.UUID,
        name: str,
        description: str | None = None,
        parent_id: uuid.UUID | None = None,
    ) -> Category:
        """Create a new category.

        Args:
            actor_id: UUID of the actor performing the operation.
            name: Category name.
            description: Optional long-form description.
            parent_id: UUID of the parent category, or None for a root category.

        Returns:
            The newly created Category instance.

        Raises:
            CategoryNotFound: If parent_id is provided but does not exist.
            CategoryAlreadyExists: If a category with the same name and parent
                already exists.
        """
        if parent_id is not None and self.repo.get_by_id(parent_id) is None:
            # If a parent_id is provided but does not exist, raise an error.
            raise CategoryNotFound(parent_id)
        if self.repo.get_by_name(name, parent_id) is not None:
            raise CategoryAlreadyExists(name)
        try:
            category = self.repo.create(
                name=name, description=description, parent_id=parent_id
            )
        except IntegrityError:
            raise CategoryAlreadyExists(name) from None
        logger.info("Category created: %s", category.id)
        from app.shared.observability import current_trace_id

        record_audit(
            self._audit,
            actor_id=actor_id,
            operation="create",
            action="catalog.category_created",
            aggregate_type="category",
            aggregate_id=category.id,
            domain=_DOMAIN,
            changes={
                "name": FieldChange(before=None, after=name),
                "description": FieldChange(before=None, after=description),
                "parent_id": FieldChange(
                    before=None, after=str(parent_id) if parent_id else None
                ),
            },
        )
        _publish(
            self._broker,
            "catalog.category.created",
            "CategoryCreated",
            "category",
            category.id,
            {
                "name": name,
                "description": description,
                "parent_id": str(parent_id) if parent_id else None,
            },
            current_trace_id(),
        )
        return category

    def get(self, category_id: uuid.UUID) -> Category:
        """Return the category with the given id.

        Args:
            category_id: The UUID of the category.

        Returns:
            The Category instance.
        Raises:
            CategoryNotFound: If no active category with the given id exists.
        """
        category = self.repo.get_by_id(category_id)
        if category is None:
            raise CategoryNotFound(category_id)
        return category

    def update(
        self, actor_id: uuid.UUID, category_id: uuid.UUID, data: dict[str, Any]
    ) -> Category:
        """Apply a partial update to a category.

        Args:
            actor_id: UUID of the actor performing the operation.
            category_id: The UUID of the category to update.
            data: A dict of field names to new values.

        Returns:
            The updated Category instance.
        Raises:
            CategoryNotFound: If no active category with the given id exists.
            CategoryAlreadyExists: If the new name conflicts with a sibling category.
        """
        category = self.repo.get_by_id(category_id)
        if category is None:
            raise CategoryNotFound(category_id)
        if "name" in data:
            parent_id = data.get("parent_id", category.parent_id)
            conflict = self.repo.get_by_name(data["name"], parent_id)
            if conflict is not None and conflict.id != category_id:
                raise CategoryAlreadyExists(data["name"])
        before = {k: getattr(category, k) for k in data}
        try:
            updated = self.repo.update(category, data)
        except IntegrityError:
            raise CategoryAlreadyExists(data.get("name", "")) from None
        record_audit(
            self._audit,
            actor_id=actor_id,
            operation="update",
            action="catalog.category_updated",
            aggregate_type="category",
            aggregate_id=category_id,
            domain=_DOMAIN,
            changes={k: FieldChange(before=before[k], after=data[k]) for k in data},
        )
        from app.shared.observability import current_trace_id

        _publish(
            self._broker,
            "catalog.category.updated",
            "CategoryUpdated",
            "category",
            category_id,
            data,
            current_trace_id(),
        )
        return updated

    def delete(self, actor_id: uuid.UUID, category_id: uuid.UUID) -> None:
        """Soft-delete a category.

        Args:
            actor_id: UUID of the actor performing the operation.
            category_id: The UUID of the category to delete.
        Raises:
            CategoryNotFound: If no active category with the given id exists.
        """
        category = self.repo.get_by_id(category_id)
        if category is None:
            raise CategoryNotFound(category_id)
        self.repo.delete(category)
        logger.info("Category deleted: %s", category_id)
        record_audit(
            self._audit,
            actor_id=actor_id,
            operation="delete",
            action="catalog.category_deleted",
            aggregate_type="category",
            aggregate_id=category_id,
            domain=_DOMAIN,
            changes=None,
        )
        from app.shared.observability import current_trace_id

        _publish(
            self._broker,
            "catalog.category.deleted",
            "CategoryDeleted",
            "category",
            category_id,
            {"category_id": str(category_id)},
            current_trace_id(),
        )

    def list_root(
        self, limit: int = PAGE_SIZE, cursor: tuple[datetime, uuid.UUID] | None = None
    ) -> list[Category]:
        """Return a page of active root categories.

        Args:
            limit: Maximum number of records to return.
            cursor: Keyset cursor (created_at, id) for pagination.

        Returns:
            A list of root Category instances.
        """
        return self.repo.list_root(limit, cursor)

    def list_by_parent(
        self,
        parent_id: uuid.UUID,
        limit: int = PAGE_SIZE,
        cursor: tuple[datetime, uuid.UUID] | None = None,
    ) -> list[Category]:
        """Return a page of active child categories under the given parent.

        Args:
            parent_id: The UUID of the parent category.
            limit: Maximum number of records to return.
            cursor: Keyset cursor (created_at, id) for pagination.

        Returns:
            A list of child Category instances.
        Raises:
            CategoryNotFound: If no active category with the given parent_id exists.
        """
        if self.repo.get_by_id(parent_id) is None:
            raise CategoryNotFound(parent_id)
        return self.repo.list_by_parent(parent_id, limit, cursor)


class BrandService:
    """Manages brand creation, updates, and soft-deletion.

    All write operations flush within the service but do not commit —
    the caller (route handler) owns the transaction boundary.
    """

    def __init__(
        self, session: Session, audit: AuditPort, broker: MessageBroker
    ) -> None:
        """Initialize with an active session, audit port, and message broker.

        Args:
            session: The SQLAlchemy session scoped to the current request.
            audit: The audit port used to record state-changing operations.
            broker: The message broker port used to publish domain events.
        """
        self.repo = BrandRepository(session)
        self._audit = audit
        self._broker = broker

    def create(self, actor_id: uuid.UUID, name: str, **kwargs: Any) -> Brand:
        """Create a new brand.

        Args:
            actor_id: UUID of the actor performing the operation.
            name: Unique brand name.
            **kwargs: Optional brand fields (website, contact_email, description).

        Returns:
            The newly created Brand instance.
        Raises:
            BrandAlreadyExists: If a brand with the given name already exists.
        """
        if self.repo.get_by_name(name) is not None:
            raise BrandAlreadyExists(name)
        try:
            brand = self.repo.create(name=name, **kwargs)
        except IntegrityError:
            raise BrandAlreadyExists(name) from None
        logger.info("Brand created: %s", brand.id)
        from app.shared.observability import current_trace_id

        changes = {"name": FieldChange(before=None, after=name)}
        changes.update(
            {k: FieldChange(before=None, after=v) for k, v in kwargs.items()}
        )
        record_audit(
            self._audit,
            actor_id=actor_id,
            operation="create",
            action="catalog.brand_created",
            aggregate_type="brand",
            aggregate_id=brand.id,
            domain=_DOMAIN,
            changes=changes,
        )
        _publish(
            self._broker,
            "catalog.brand.created",
            "BrandCreated",
            "brand",
            brand.id,
            {"name": name, **kwargs},
            current_trace_id(),
        )
        return brand

    def get(self, brand_id: uuid.UUID) -> Brand:
        """Return the brand with the given id.

        Args:
            brand_id: The UUID of the brand.

        Returns:
            The Brand instance.
        Raises:
            BrandNotFound: If no active brand with the given id exists.
        """
        brand = self.repo.get_by_id(brand_id)
        if brand is None:
            raise BrandNotFound(brand_id)
        return brand

    def update(
        self, actor_id: uuid.UUID, brand_id: uuid.UUID, data: dict[str, Any]
    ) -> Brand:
        """Apply a partial update to a brand.

        Args:
            actor_id: UUID of the actor performing the operation.
            brand_id: The UUID of the brand to update.
            data: A dict of field names to new values.

        Returns:
            The updated Brand instance.
        Raises:
            BrandNotFound: If no active brand with the given id exists.
            BrandAlreadyExists: If the new name conflicts with an existing brand.
        """
        brand = self.repo.get_by_id(brand_id)
        if brand is None:
            raise BrandNotFound(brand_id)
        if "name" in data:
            conflict = self.repo.get_by_name(data["name"])
            if conflict is not None and conflict.id != brand_id:
                raise BrandAlreadyExists(data["name"])
        before = {k: getattr(brand, k) for k in data}
        try:
            updated = self.repo.update(brand, data)
        except IntegrityError:
            raise BrandAlreadyExists(data.get("name", "")) from None
        record_audit(
            self._audit,
            actor_id=actor_id,
            operation="update",
            action="catalog.brand_updated",
            aggregate_type="brand",
            aggregate_id=brand_id,
            domain=_DOMAIN,
            changes={k: FieldChange(before=before[k], after=data[k]) for k in data},
        )
        from app.shared.observability import current_trace_id

        _publish(
            self._broker,
            "catalog.brand.updated",
            "BrandUpdated",
            "brand",
            brand_id,
            data,
            current_trace_id(),
        )
        return updated

    def delete(self, actor_id: uuid.UUID, brand_id: uuid.UUID) -> None:
        """Soft-delete a brand.

        Args:
            actor_id: UUID of the actor performing the operation.
            brand_id: The UUID of the brand to delete.
        Raises:
            BrandNotFound: If no active brand with the given id exists.
        """
        brand = self.repo.get_by_id(brand_id)
        if brand is None:
            raise BrandNotFound(brand_id)
        self.repo.delete(brand)
        logger.info("Brand deleted: %s", brand_id)
        record_audit(
            self._audit,
            actor_id=actor_id,
            operation="delete",
            action="catalog.brand_deleted",
            aggregate_type="brand",
            aggregate_id=brand_id,
            domain=_DOMAIN,
            changes=None,
        )
        from app.shared.observability import current_trace_id

        _publish(
            self._broker,
            "catalog.brand.deleted",
            "BrandDeleted",
            "brand",
            brand_id,
            {"brand_id": str(brand_id)},
            current_trace_id(),
        )


class ProductService:
    """Manages product creation, updates, status transitions, and soft-deletion.

    All write operations flush within the service but do not commit —
    the caller (route handler) owns the transaction boundary.
    """

    def __init__(
        self, session: Session, audit: AuditPort, broker: MessageBroker
    ) -> None:
        """Initialize with an active session, audit port, and message broker.

        Args:
            session: The SQLAlchemy session scoped to the current request.
            audit: The audit port used to record state-changing operations.
            broker: The message broker port used to publish domain events.
        """
        self.repo = ProductRepository(session)
        self._category_repo = CategoryRepository(session)
        self._brand_repo = BrandRepository(session)
        self._audit = audit
        self._broker = broker

    def create(
        self, actor_id: uuid.UUID, sku: str, name: str, base_price: Any, **kwargs: Any
    ) -> Product:
        """Create a new product.

        Args:
            actor_id: UUID of the actor performing the operation.
            sku: Unique stock-keeping unit.
            name: Product display name.
            base_price: Listed price in the base currency.
            **kwargs: Optional fields (description, category_id, brand_id, status,
                specs).

        Returns:
            The newly created Product instance.
        Raises:
            CategoryNotFound: If category_id is provided but does not exist.
            BrandNotFound: If brand_id is provided but does not exist.
            ProductAlreadyExists: If a product with the given SKU already exists.
        """
        category_id = kwargs.get("category_id")
        brand_id = kwargs.get("brand_id")
        if (
            category_id is not None
            and self._category_repo.get_by_id(category_id) is None
        ):
            raise CategoryNotFound(category_id)
        if brand_id is not None and self._brand_repo.get_by_id(brand_id) is None:
            raise BrandNotFound(brand_id)
        if self.repo.get_by_sku(sku) is not None:
            raise ProductAlreadyExists(sku)
        try:
            product = self.repo.create(
                sku=sku, name=name, base_price=base_price, **kwargs
            )
        except IntegrityError:
            raise ProductAlreadyExists(sku) from None
        logger.info("Product created: %s", product.id)
        from app.shared.observability import current_trace_id

        changes = {
            "sku": FieldChange(before=None, after=sku),
            "name": FieldChange(before=None, after=name),
            "base_price": FieldChange(before=None, after=str(base_price)),
        }
        changes.update(
            {k: FieldChange(before=None, after=v) for k, v in kwargs.items()}
        )
        record_audit(
            self._audit,
            actor_id=actor_id,
            operation="create",
            action="catalog.product_created",
            aggregate_type="product",
            aggregate_id=product.id,
            domain=_DOMAIN,
            changes=changes,
        )
        _publish(
            self._broker,
            "catalog.product.created",
            "ProductCreated",
            "product",
            product.id,
            {
                "sku": sku,
                "name": name,
                "base_price": str(base_price),
                **{
                    k: str(v) if isinstance(v, uuid.UUID) else v
                    for k, v in kwargs.items()
                },
            },
            current_trace_id(),
        )
        return product

    def get(self, product_id: uuid.UUID) -> Product:
        """Return the product with the given id.

        Args:
            product_id: The UUID of the product.

        Returns:
            The Product instance.
        Raises:
            ProductNotFound: If no active product with the given id exists.
        """
        product = self.repo.get_by_id(product_id)
        if product is None:
            raise ProductNotFound(product_id)
        return product

    def update(
        self, actor_id: uuid.UUID, product_id: uuid.UUID, data: dict[str, Any]
    ) -> Product:
        """Apply a partial update to a product.

        Args:
            actor_id: UUID of the actor performing the operation.
            product_id: The UUID of the product to update.
            data: A dict of field names to new values.

        Returns:
            The updated Product instance.
        Raises:
            ProductNotFound: If no active product with the given id exists.
            CategoryNotFound: If category_id in data does not exist.
            BrandNotFound: If brand_id in data does not exist.
            ProductAlreadyExists: If the new SKU conflicts with an existing product.
        """
        product = self.repo.get_by_id(product_id)
        if product is None:
            raise ProductNotFound(product_id)
        category_id = data.get("category_id")
        brand_id = data.get("brand_id")
        if category_id is not None and (
            self._category_repo.get_by_id(category_id) is None
        ):
            raise CategoryNotFound(category_id)
        if brand_id is not None and self._brand_repo.get_by_id(brand_id) is None:
            raise BrandNotFound(brand_id)
        if "sku" in data:
            conflict = self.repo.get_by_sku(data["sku"])
            if conflict is not None and conflict.id != product_id:
                raise ProductAlreadyExists(data["sku"])
        before = {k: getattr(product, k) for k in data}
        try:
            updated = self.repo.update(product, data)
        except IntegrityError:
            raise ProductAlreadyExists(data.get("sku", "")) from None
        record_audit(
            self._audit,
            actor_id=actor_id,
            operation="update",
            action="catalog.product_updated",
            aggregate_type="product",
            aggregate_id=product_id,
            domain=_DOMAIN,
            changes={k: FieldChange(before=before[k], after=data[k]) for k in data},
        )
        from app.shared.observability import current_trace_id

        _publish(
            self._broker,
            "catalog.product.updated",
            "ProductUpdated",
            "product",
            product_id,
            data,
            current_trace_id(),
        )
        return updated

    def delete(self, actor_id: uuid.UUID, product_id: uuid.UUID) -> None:
        """Soft-delete a product.

        Args:
            actor_id: UUID of the actor performing the operation.
            product_id: The UUID of the product to delete.
        Raises:
            ProductNotFound: If no active product with the given id exists.
        """
        product = self.repo.get_by_id(product_id)
        if product is None:
            raise ProductNotFound(product_id)
        self.repo.delete(product)
        logger.info("Product deleted: %s", product_id)
        record_audit(
            self._audit,
            actor_id=actor_id,
            operation="delete",
            action="catalog.product_deleted",
            aggregate_type="product",
            aggregate_id=product_id,
            domain=_DOMAIN,
            changes=None,
        )
        from app.shared.observability import current_trace_id

        _publish(
            self._broker,
            "catalog.product.deleted",
            "ProductDeleted",
            "product",
            product_id,
            {"product_id": str(product_id)},
            current_trace_id(),
        )

    def list_by_category(
        self,
        category_id: uuid.UUID,
        limit: int = PAGE_SIZE,
        cursor: tuple[datetime, uuid.UUID] | None = None,
    ) -> list[Product]:
        """Return a page of active products in the given category.

        Args:
            category_id: The UUID of the category.
            limit: Maximum number of records to return.
            cursor: Keyset cursor (created_at, id) for pagination.

        Returns:
            A list of Product instances.
        Raises:
            CategoryNotFound: If no active category with the given id exists.
        """
        if self._category_repo.get_by_id(category_id) is None:
            raise CategoryNotFound(category_id)
        return self.repo.list_by_category(category_id, limit, cursor)

    def list_by_brand(
        self,
        brand_id: uuid.UUID,
        limit: int = PAGE_SIZE,
        cursor: tuple[datetime, uuid.UUID] | None = None,
    ) -> list[Product]:
        """Return a page of active products for the given brand.

        Args:
            brand_id: The UUID of the brand.
            limit: Maximum number of records to return.
            cursor: Keyset cursor (created_at, id) for pagination.

        Returns:
            A list of Product instances.
        Raises:
            BrandNotFound: If no active brand with the given id exists.
        """
        if self._brand_repo.get_by_id(brand_id) is None:
            raise BrandNotFound(brand_id)
        return self.repo.list_by_brand(brand_id, limit, cursor)


def _collect_category_attributes(
    category_repo: CategoryRepository,
    attr_repo: CategoryAttributeRepository,
    category_id: uuid.UUID,
) -> list[CategoryAttribute]:
    """Collect all attribute definitions for a category, including inherited ones.

    Traverses the category hierarchy from the given category up to the root,
    accumulating attribute definitions. Child definitions take precedence over
    parent definitions for the same key.

    Args:
        category_repo: Repository for category lookups.
        attr_repo: Repository for category attribute lookups.
        category_id: The UUID of the category to resolve attributes for.

    Returns:
        A list of CategoryAttribute definitions, child definitions taking
        precedence over parent definitions for the same key.
    """
    seen_keys: set[str] = set()
    result: list[CategoryAttribute] = []
    current_id: uuid.UUID | None = category_id
    while current_id is not None:
        attrs = attr_repo.list_by_category(current_id, limit=1000)
        for attr in attrs:
            if attr.key not in seen_keys:
                seen_keys.add(attr.key)
                result.append(attr)
        category: Category | None = category_repo.get_by_id(current_id)
        current_id = category.parent_id if category is not None else None
    return result


def _validate_variant_attributes(
    attributes: dict[str, Any],
    schema: list[CategoryAttribute],
) -> None:
    """Validate variant attributes against the resolved category attribute schema.

    Args:
        attributes: The variant's attribute dict to validate.
        schema: The resolved list of CategoryAttribute definitions (including
            inherited).
    Raises:
        InvalidVariantAttributes: If any required attribute is missing or a value
            type does not match the declared value_type.
    """
    _type_map: dict[str, type] = {
        "string": str,
        "number": (int, float),  # type: ignore[dict-item]
        "boolean": bool,
        "object": dict,
    }
    violations: dict[str, str] = {}
    for attr in schema:
        value = attributes.get(attr.key)
        if value is None:
            if attr.required:
                violations[attr.key] = "required attribute is missing"
            continue
        expected = _type_map.get(attr.value_type)
        if expected is not None and not isinstance(value, expected):
            violations[attr.key] = (
                f"expected {attr.value_type}, got {type(value).__name__}"
            )
    if violations:
        raise InvalidVariantAttributes(violations)


class VariantService:
    """Manages variant creation, updates, and soft-deletion.

    Validates variant attributes against the resolved category attribute schema
    (including inherited attributes from parent categories) before persisting.

    All write operations flush within the service but do not commit —
    the caller (route handler) owns the transaction boundary.
    """

    def __init__(
        self, session: Session, audit: AuditPort, broker: MessageBroker
    ) -> None:
        """Initialize with an active session, audit port, and message broker.

        Args:
            session: The SQLAlchemy session scoped to the current request.
            audit: The audit port used to record state-changing operations.
            broker: The message broker port used to publish domain events.
        """
        self.repo = VariantRepository(session)
        self._product_repo = ProductRepository(session)
        self._category_repo = CategoryRepository(session)
        self._attr_repo = CategoryAttributeRepository(session)
        self._audit = audit
        self._broker = broker

    def _resolve_schema(self, product_id: uuid.UUID) -> list[CategoryAttribute]:
        """Return the resolved attribute schema for the product's category.

        Returns an empty list if the product has no category assigned.

        Args:
            product_id: The UUID of the product.

        Returns:
            A list of CategoryAttribute definitions, or an empty list if the
            product has no category.
        """
        product = self._product_repo.get_by_id(product_id)
        if product is None or product.category_id is None:
            return []
        return _collect_category_attributes(
            self._category_repo, self._attr_repo, product.category_id
        )

    def create(
        self,
        actor_id: uuid.UUID,
        product_id: uuid.UUID,
        sku: str,
        price: Any,
        attributes: dict[str, Any] | None = None,
    ) -> Variant:
        """Create a new variant for the given product.

        Args:
            actor_id: UUID of the actor performing the operation.
            product_id: UUID of the parent product.
            sku: Unique stock-keeping unit for this variant.
            price: Listed price for this variant.
            attributes: Variant attribute dict validated against the category schema.

        Returns:
            The newly created Variant instance.
        Raises:
            ProductNotFound: If no active product with the given product_id exists.
            VariantAlreadyExists: If a variant with the given SKU already exists.
            InvalidVariantAttributes: If attributes fail the category schema validation.
        """
        if self._product_repo.get_by_id(product_id) is None:
            raise ProductNotFound(product_id)
        if self.repo.get_by_sku(sku) is not None:
            raise VariantAlreadyExists(sku)
        attrs = attributes or {}
        schema = self._resolve_schema(product_id)
        if schema:
            _validate_variant_attributes(attrs, schema)
        try:
            variant = self.repo.create(
                product_id=product_id, sku=sku, price=price, attributes=attrs
            )
        except IntegrityError:
            raise VariantAlreadyExists(sku) from None
        logger.info("Variant created: %s", variant.id)
        from app.shared.observability import current_trace_id

        record_audit(
            self._audit,
            actor_id=actor_id,
            operation="create",
            action="catalog.variant_created",
            aggregate_type="variant",
            aggregate_id=variant.id,
            domain=_DOMAIN,
            changes={
                "product_id": FieldChange(before=None, after=str(product_id)),
                "sku": FieldChange(before=None, after=sku),
                "price": FieldChange(before=None, after=str(price)),
                "attributes": FieldChange(before=None, after=attrs),
            },
        )
        _publish(
            self._broker,
            "catalog.variant.created",
            "VariantCreated",
            "variant",
            variant.id,
            {
                "product_id": str(product_id),
                "sku": sku,
                "price": str(price),
                "attributes": attrs,
            },
            current_trace_id(),
        )
        return variant

    def get(self, variant_id: uuid.UUID) -> Variant:
        """Return the variant with the given id.

        Args:
            variant_id: The UUID of the variant.

        Returns:
            The Variant instance.
        Raises:
            VariantNotFound: If no active variant with the given id exists.
        """
        variant = self.repo.get_by_id(variant_id)
        if variant is None:
            raise VariantNotFound(variant_id)
        return variant

    def update(
        self, actor_id: uuid.UUID, variant_id: uuid.UUID, data: dict[str, Any]
    ) -> Variant:
        """Apply a partial update to a variant.

        Args:
            actor_id: UUID of the actor performing the operation.
            variant_id: The UUID of the variant to update.
            data: A dict of field names to new values.

        Returns:
            The updated Variant instance.
        Raises:
            VariantNotFound: If no active variant with the given id exists.
            VariantAlreadyExists: If the new SKU conflicts with an existing variant.
            InvalidVariantAttributes: If updated attributes fail the category
                schema validation.
        """
        variant = self.repo.get_by_id(variant_id)
        if variant is None:
            raise VariantNotFound(variant_id)
        if "sku" in data:
            conflict = self.repo.get_by_sku(data["sku"])
            if conflict is not None and conflict.id != variant_id:
                raise VariantAlreadyExists(data["sku"])
        if "attributes" in data:
            schema = self._resolve_schema(variant.product_id)
            if schema:
                merged = {**variant.attributes, **data["attributes"]}
                _validate_variant_attributes(merged, schema)
        before = {k: getattr(variant, k) for k in data}
        try:
            updated = self.repo.update(variant, data)
        except IntegrityError:
            raise VariantAlreadyExists(data.get("sku", "")) from None
        record_audit(
            self._audit,
            actor_id=actor_id,
            operation="update",
            action="catalog.variant_updated",
            aggregate_type="variant",
            aggregate_id=variant_id,
            domain=_DOMAIN,
            changes={k: FieldChange(before=before[k], after=data[k]) for k in data},
        )
        from app.shared.observability import current_trace_id

        _publish(
            self._broker,
            "catalog.variant.updated",
            "VariantUpdated",
            "variant",
            variant_id,
            data,
            current_trace_id(),
        )
        return updated

    def delete(self, actor_id: uuid.UUID, variant_id: uuid.UUID) -> None:
        """Soft-delete a variant.

        Args:
            actor_id: UUID of the actor performing the operation.
            variant_id: The UUID of the variant to delete.
        Raises:
            VariantNotFound: If no active variant with the given id exists.
        """
        variant = self.repo.get_by_id(variant_id)
        if variant is None:
            raise VariantNotFound(variant_id)
        self.repo.delete(variant)
        logger.info("Variant deleted: %s", variant_id)
        record_audit(
            self._audit,
            actor_id=actor_id,
            operation="delete",
            action="catalog.variant_deleted",
            aggregate_type="variant",
            aggregate_id=variant_id,
            domain=_DOMAIN,
            changes=None,
        )
        from app.shared.observability import current_trace_id

        _publish(
            self._broker,
            "catalog.variant.deleted",
            "VariantDeleted",
            "variant",
            variant_id,
            {"variant_id": str(variant_id)},
            current_trace_id(),
        )

    def list_by_product(
        self,
        product_id: uuid.UUID,
        limit: int = PAGE_SIZE,
        cursor: tuple[datetime, uuid.UUID] | None = None,
    ) -> list[Variant]:
        """Return a page of active variants for the given product.

        Args:
            product_id: The UUID of the parent product.
            limit: Maximum number of records to return.
            cursor: Keyset cursor (created_at, id) for pagination.

        Returns:
            A list of Variant instances.
        Raises:
            ProductNotFound: If no active product with the given id exists.
        """
        if self._product_repo.get_by_id(product_id) is None:
            raise ProductNotFound(product_id)
        return self.repo.list_by_product(product_id, limit, cursor)


class CategoryAttributeService:
    """Manages category attribute definition creation, updates, and deletion.

    All write operations flush within the service but do not commit —
    the caller (route handler) owns the transaction boundary.
    """

    def __init__(
        self, session: Session, audit: AuditPort, broker: MessageBroker
    ) -> None:
        """Initialize with an active session, audit port, and message broker.

        Args:
            session: The SQLAlchemy session scoped to the current request.
            audit: The audit port used to record state-changing operations.
            broker: The message broker port used to publish domain events.
        """
        self.repo = CategoryAttributeRepository(session)
        self._category_repo = CategoryRepository(session)
        self._audit = audit
        self._broker = broker

    def create(
        self,
        actor_id: uuid.UUID,
        category_id: uuid.UUID,
        key: str,
        value_type: str,
        required: bool = False,
    ) -> CategoryAttribute:
        """Create a new attribute definition for a category.

        Args:
            actor_id: UUID of the actor performing the operation.
            category_id: UUID of the category this attribute applies to.
            key: Attribute dimension name (e.g. color, size).
            value_type: Expected value type (string, number, boolean, object).
            required: Whether variants must supply this attribute.

        Returns:
            The newly created CategoryAttribute instance.
        Raises:
            CategoryNotFound: If no active category with the given id exists.
            CategoryAttributeAlreadyExists: If the key already exists for this category.
        """
        if self._category_repo.get_by_id(category_id) is None:
            raise CategoryNotFound(category_id)
        if self.repo.get_by_category_and_key(category_id, key) is not None:
            raise CategoryAttributeAlreadyExists(f"{category_id}/{key}")
        try:
            attr = self.repo.create(
                category_id=category_id,
                key=key,
                value_type=value_type,
                required=required,
            )
        except IntegrityError:
            raise CategoryAttributeAlreadyExists(f"{category_id}/{key}") from None
        logger.info("CategoryAttribute created: %s", attr.id)
        from app.shared.observability import current_trace_id

        record_audit(
            self._audit,
            actor_id=actor_id,
            operation="create",
            action="catalog.category_attribute_created",
            aggregate_type="category_attribute",
            aggregate_id=attr.id,
            domain=_DOMAIN,
            changes={
                "category_id": FieldChange(before=None, after=str(category_id)),
                "key": FieldChange(before=None, after=key),
                "value_type": FieldChange(before=None, after=value_type),
                "required": FieldChange(before=None, after=required),
            },
        )
        _publish(
            self._broker,
            "catalog.category_attribute.created",
            "CategoryAttributeCreated",
            "category_attribute",
            attr.id,
            {
                "category_id": str(category_id),
                "key": key,
                "value_type": value_type,
                "required": required,
            },
            current_trace_id(),
        )
        return attr

    def get(self, attribute_id: uuid.UUID) -> CategoryAttribute:
        """Return the category attribute with the given id.

        Args:
            attribute_id: The UUID of the category attribute.

        Returns:
            The CategoryAttribute instance.
        Raises:
            CategoryAttributeNotFound: If no attribute with the given id exists.
        """
        attr = self.repo.get_by_id(attribute_id)
        if attr is None:
            raise CategoryAttributeNotFound(attribute_id)
        return attr

    def update(
        self, actor_id: uuid.UUID, attribute_id: uuid.UUID, data: dict[str, Any]
    ) -> CategoryAttribute:
        """Apply a partial update to a category attribute definition.

        Args:
            actor_id: UUID of the actor performing the operation.
            attribute_id: The UUID of the attribute to update.
            data: A dict of field names to new values.

        Returns:
            The updated CategoryAttribute instance.
        Raises:
            CategoryAttributeNotFound: If no attribute with the given id exists.
            CategoryAttributeAlreadyExists: If the new key conflicts with an
                existing one.
        """
        attr = self.repo.get_by_id(attribute_id)
        if attr is None:
            raise CategoryAttributeNotFound(attribute_id)
        if "key" in data:
            conflict = self.repo.get_by_category_and_key(attr.category_id, data["key"])
            if conflict is not None and conflict.id != attribute_id:
                raise CategoryAttributeAlreadyExists(
                    f"{attr.category_id}/{data['key']}"
                )
        before = {k: getattr(attr, k) for k in data}
        try:
            updated = self.repo.update(attr, data)
        except IntegrityError:
            raise CategoryAttributeAlreadyExists(
                f"{attr.category_id}/{data.get('key', '')}"
            ) from None
        record_audit(
            self._audit,
            actor_id=actor_id,
            operation="update",
            action="catalog.category_attribute_updated",
            aggregate_type="category_attribute",
            aggregate_id=attribute_id,
            domain=_DOMAIN,
            changes={k: FieldChange(before=before[k], after=data[k]) for k in data},
        )
        from app.shared.observability import current_trace_id

        _publish(
            self._broker,
            "catalog.category_attribute.updated",
            "CategoryAttributeUpdated",
            "category_attribute",
            attribute_id,
            data,
            current_trace_id(),
        )
        return updated

    def delete(self, actor_id: uuid.UUID, attribute_id: uuid.UUID) -> None:
        """Hard-delete a category attribute definition.

        CategoryAttribute does not support soft delete — the row is removed.

        Args:
            actor_id: UUID of the actor performing the operation.
            attribute_id: The UUID of the attribute to delete.
        Raises:
            CategoryAttributeNotFound: If no attribute with the given id exists.
        """
        attr = self.repo.get_by_id(attribute_id)
        if attr is None:
            raise CategoryAttributeNotFound(attribute_id)
        self.repo.delete(attr)
        logger.info("CategoryAttribute deleted: %s", attribute_id)
        record_audit(
            self._audit,
            actor_id=actor_id,
            operation="delete",
            action="catalog.category_attribute_deleted",
            aggregate_type="category_attribute",
            aggregate_id=attribute_id,
            domain=_DOMAIN,
            changes=None,
        )
        from app.shared.observability import current_trace_id

        _publish(
            self._broker,
            "catalog.category_attribute.deleted",
            "CategoryAttributeDeleted",
            "category_attribute",
            attribute_id,
            {"attribute_id": str(attribute_id)},
            current_trace_id(),
        )

    def list_by_category(
        self,
        category_id: uuid.UUID,
        limit: int = PAGE_SIZE,
        cursor: tuple[datetime, uuid.UUID] | None = None,
    ) -> list[CategoryAttribute]:
        """Return a page of attribute definitions for the given category.

        Args:
            category_id: The UUID of the category.
            limit: Maximum number of records to return.
            cursor: Keyset cursor (created_at, id) for pagination.

        Returns:
            A list of CategoryAttribute instances.
        Raises:
            CategoryNotFound: If no active category with the given id exists.
        """
        if self._category_repo.get_by_id(category_id) is None:
            raise CategoryNotFound(category_id)
        return self.repo.list_by_category(category_id, limit, cursor)
