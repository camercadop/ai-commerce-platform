# Writing Models

How to define SQLAlchemy ORM models consistently across all domains.

See [ADR-001: Service Boundaries and Domain Ownership](../adr/001-service-boundaries-and-domain-ownership.md)
for the rationale on domain data ownership.

---

## Inheritance

Every domain model must inherit from `TimestampMixin` and `BaseModel`. `BaseModel` is
the declarative base. `TimestampMixin` provides `created_at` and `updated_at`.

```python
from app.shared.db import BaseModel, TimestampMixin


class Product(TimestampMixin, BaseModel):
    __tablename__ = "catalog_products"
```

Every model must declare its own UUID primary key as the first column. This ensures
`id` appears first in the migration output and the database table definition.

Declare class attributes in this order:
1. `__tablename__`
2. `__table_args__` (if any)
3. `id` primary key
4. remaining columns
5. relationships

```python
import uuid
from sqlalchemy import UUID
from sqlalchemy.orm import Mapped, mapped_column


class Product(TimestampMixin, BaseModel):
    __tablename__ = "catalog_products"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    # Unique identifier for this product.
```

Add `SoftDeleteMixin` to models that require soft delete support. It provides a
`deleted_at` timestamp column. A null value means the record is active; a non-null
value means it has been soft-deleted.

```python
from app.shared.db import BaseModel, SoftDeleteMixin, TimestampMixin


class Order(SoftDeleteMixin, TimestampMixin, BaseModel):
    __tablename__ = "commerce_orders"
```

Never physically delete rows from models that use `SoftDeleteMixin`. All queries
against soft-deletable models must filter `deleted_at IS NULL` to exclude deleted
records.

---

## Docstrings

Every model class must have a docstring immediately after the class declaration.
The docstring must describe what the entity represents and any non-obvious ownership
or lifecycle rules. It must not restate the table name or list the columns.

```python
# wrong — no docstring
class Address(SoftDeleteMixin, TimestampMixin, BaseModel):
    __tablename__ = "identity_customer_addresses"


# wrong — restates columns
class Address(SoftDeleteMixin, TimestampMixin, BaseModel):
    """Has id, customer_id, street, city, state, country, postal_code."""


# correct
class Address(SoftDeleteMixin, TimestampMixin, BaseModel):
    """A physical address associated with a customer.

    A customer may have multiple addresses. Only one address per customer
    may be marked as the default.
    """
```

---

## Columns

Use SQLAlchemy 2.x typed annotations (`Mapped`, `mapped_column`) for all column
definitions. Do not use the legacy `Column(...)` style.

```python
# wrong
name = Column(String(255), nullable=False)

# correct
name: Mapped[str] = mapped_column(String(255), nullable=False)
```

Every field must have a single-line comment immediately below it explaining its
purpose. The comment must describe what the field represents, not restate its type.

```python
name: Mapped[str] = mapped_column(String(255), nullable=False)
# Human-readable product name displayed in the catalog.

price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
# Listed price in the store's base currency at the time of creation.
```

Never use string literals in type annotations — use the type directly.

---

## Defaults

Use `default` for values generated in Python — UUIDs, booleans, string enums.
Use `server_default` for database-native defaults — empty JSON objects, SQL expressions.

```python
# Python-generated default
id: Mapped[uuid.UUID] = mapped_column(
    UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
)
status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
is_default: Mapped[bool] = mapped_column(nullable=False, default=False)

# Database-native default
attributes: Mapped[dict[str, Any]] = mapped_column(
    JSONB, nullable=False, server_default="{}"
)
```

---

## Naming

### Tables

Lowercase snake_case, plural. Tables must be prefixed to group related entities
together. The prefix is typically the domain name or a shared parent resource name.
Choose the shortest prefix that still communicates the grouping clearly.

```python
# wrong — no prefix, ungrouped
__tablename__ = "customers"
__tablename__ = "addresses"
__tablename__ = "preferences"

# correct — grouped by domain and parent resource
__tablename__ = "identity_customers"
__tablename__ = "identity_customer_addresses"
__tablename__ = "identity_customer_preferences"
```

### Columns

Lowercase snake_case. The primary key is always `id`.

```python
# wrong
fullName: Mapped[str] = ...
FullName: Mapped[str] = ...

# correct
full_name: Mapped[str] = ...
```

### Foreign key columns

`<referenced_table_singular>_id`.

```python
# wrong
customer: Mapped[uuid.UUID] = ...
customer_fk: Mapped[uuid.UUID] = ...

# correct
customer_id: Mapped[uuid.UUID] = ...
```

### Boolean columns

`is_` or `has_` prefix.

```python
# wrong
default: Mapped[bool] = ...
verified_email: Mapped[bool] = ...

# correct
is_default: Mapped[bool] = ...
has_verified_email: Mapped[bool] = ...
```

### Timestamp columns

`_at` suffix.

```python
# wrong
created: Mapped[datetime] = ...
cancellation_time: Mapped[datetime] = ...

# correct
created_at: Mapped[datetime] = ...
cancelled_at: Mapped[datetime] = ...
```

### Constraints and indexes

| Type | Pattern | Example |
| --- | --- | --- |
| Foreign key | `fk_<table>_<column>` | `fk_addresses_customer_id` |
| Index | `idx_<table>_<column>` | `idx_customers_email` |
| Unique constraint | `uq_<table>_<column>` | `uq_customers_email` |
| Check constraint | `ck_<table>_<description>` | `ck_orders_positive_total` |

---

## Relationships

Use `relationship()` for ORM-level navigation. Always set `back_populates` on both
sides. Never use `backref`, including for self-referential relationships.

For self-referential relationships, declare both sides explicitly on the same class
using `remote_side` to distinguish the many side from the one side.

```python
class Category(SoftDeleteMixin, TimestampMixin, BaseModel):
    """A product category organized in a hierarchical tree structure."""

    __tablename__ = "catalog_categories"

    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("catalog_categories.id", name="fk_catalog_categories_parent_id"),
        nullable=True,
    )
    # Identifier of the parent category, or null for root categories.

    parent_category: Mapped[Category | None] = relationship(
        "Category", back_populates="child_categories", remote_side="Category.id"
    )
    # The parent category, or null if this is a root category.

    child_categories: Mapped[list[Category]] = relationship(
        "Category", back_populates="parent_category"
    )
    # Direct child categories of this category.
```

Use `cascade="all, delete-orphan"` on the parent side of a composition — when the
children cannot exist without the parent and must be deleted with it. Do not set
`cascade` on reference relationships, where the related entity exists independently.

```python
# composition — cart owns its items
class Cart(SoftDeleteMixin, TimestampMixin, BaseModel):
    items: Mapped[list[CartItem]] = relationship(
        "CartItem", back_populates="cart", cascade="all, delete-orphan"
    )
    # Items contained in this cart.


# reference — cart item points to a variant that exists independently
class CartItem(TimestampMixin, BaseModel):
    cart: Mapped[Cart] = relationship("Cart", back_populates="items")
    # The cart this item belongs to.
```

---

## Cross-domain references

When a model references an entity owned by another domain, store the ID as a plain
column with no `ForeignKey(...)`. A database-level constraint would couple two
domain data stores, violating service boundary isolation.

Always add a comment explaining that the FK is intentionally absent and which domain
owns the referenced entity.

```python
# wrong — FK constraint crosses a domain boundary
variant_id: Mapped[uuid.UUID] = mapped_column(
    UUID(as_uuid=True),
    ForeignKey("catalog_variants.id", name="fk_cart_items_variant_id"),
    nullable=False,
)

# correct — plain column, no DB-level constraint
variant_id: Mapped[uuid.UUID] = mapped_column(
    UUID(as_uuid=True),
    nullable=False,
)
# Identifier of the product variant. No FK — variant is owned by the catalog domain.
```

---

## Constraints

Foreign key columns must declare the constraint name explicitly to make migrations
deterministic and reversible.

```python
from sqlalchemy import ForeignKey

customer_id: Mapped[uuid.UUID] = mapped_column(
    UUID(as_uuid=True),
    ForeignKey("customers.id", name="fk_addresses_customer_id"),
    nullable=False,
)
# The customer this address belongs to.
```

Add indexes for columns used in lookups or filters. Do not rely on implicit indexing
beyond the primary key.

```python
from sqlalchemy import Index


class Customer(TimestampMixin, BaseModel):
    __tablename__ = "identity_customers"

    __table_args__ = (
        Index("idx_identity_customers_email", "email", unique=True),
        Index(
            "idx_identity_customers_identity_provider_id",
            "identity_provider_id",
            unique=True,
        ),
    )
```

---

## Design

Models must only describe structure. Validation, computation, and state transitions
belong in the service layer.

```python
# wrong — business logic in the model
class Order(TimestampMixin, BaseModel):
    def cancel(self) -> None:
        if self.status == "shipped":
            raise ValueError("Cannot cancel a shipped order")
        self.status = "cancelled"


# correct — model describes structure only
class Order(TimestampMixin, BaseModel):
    __tablename__ = "commerce_orders"

    status: Mapped[str] = mapped_column(String(50), nullable=False)
    # Current lifecycle status of the order (e.g. pending, confirmed, shipped).
```
