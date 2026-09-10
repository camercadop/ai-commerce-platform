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
sides. Never use `backref`.

```python
from sqlalchemy.orm import relationship


class Customer(TimestampMixin, BaseModel):
    __tablename__ = "identity_customers"

    addresses: Mapped[list[Address]] = relationship(
        "Address", back_populates="customer"
    )
    # All addresses registered by this customer.


class Address(TimestampMixin, BaseModel):
    __tablename__ = "identity_customer_addresses"

    customer: Mapped[Customer] = relationship("Customer", back_populates="addresses")
    # The customer this address belongs to.
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
