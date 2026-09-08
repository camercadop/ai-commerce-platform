# Writing Models

How to define SQLAlchemy ORM models consistently across all domains.

See [ADR-001: Service Boundaries and Domain Ownership](../adr/001-service-boundaries-and-domain-ownership.md)
for the rationale on domain data ownership.

---

## 1. Inherit from `BaseModel`

Every domain model must inherit from `BaseModel` declared in `app/shared/db/base.py`.
`BaseModel` is abstract and provides the UUID primary key automatically.
Never inherit directly from `Base` unless the model does not require a standard UUID
primary key (e.g. association tables).

```python
from app.shared.db import BaseModel


class Product(BaseModel):
    __tablename__ = "products"
```

## 2. Do not redeclare `id`

`BaseModel` already provides the `id` UUID primary key. Never redeclare it in a
domain model.

```python
# wrong
class Product(BaseModel):
    __tablename__ = "products"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)


# correct
class Product(BaseModel):
    __tablename__ = "products"
```

## 3. Add `created_at` and `updated_at` to every model

All models must track creation and last-update timestamps. Use `server_default`
for `created_at` and `onupdate` for `updated_at` so the database sets them
independently of the application clock.

```python
from datetime import datetime
from sqlalchemy import DateTime, func


class Product(Base):
    __tablename__ = "products"

    ...

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    # Timestamp when this record was first created.

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    # Timestamp of the most recent update to this record.
```

## 4. Add a comment under every field

Every field must have a single-line comment immediately below it explaining its
purpose. The comment must describe what the field represents, not restate its type.

```python
name: Mapped[str] = mapped_column(String(255), nullable=False)
# Human-readable product name displayed in the catalog.

price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
# Listed price in the store's base currency at the time of creation.
```

## 5. Use `Mapped` and `mapped_column` for all columns

Use SQLAlchemy 2.x typed annotations (`Mapped`, `mapped_column`) for all column
definitions. Do not use the legacy `Column(...)` style.

```python
# wrong
name = Column(String(255), nullable=False)

# correct
name: Mapped[str] = mapped_column(String(255), nullable=False)
```

## 6. Naming conventions

Follow these conventions consistently across all models.

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

Lowercase snake_case. The primary key is always `id` (provided by `BaseModel`).

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

### Constraint and index names

| Type | Pattern | Example |
| --- | --- | --- |
| Foreign key | `fk_<table>_<column>` | `fk_addresses_customer_id` |
| Index | `idx_<table>_<column>` | `idx_customers_email` |
| Unique constraint | `uq_<table>_<column>` | `uq_customers_email` |
| Check constraint | `ck_<table>_<description>` | `ck_orders_positive_total` |

## 7. Define foreign keys explicitly with a named constraint

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

## 8. Declare relationships with `relationship()`

Use `relationship()` for ORM-level navigation. Always set `back_populates` on both
sides. Never use `backref`.

```python
from sqlalchemy.orm import relationship


class Customer(BaseModel):
    __tablename__ = "customers"

    addresses: Mapped[list["Address"]] = relationship(
        "Address", back_populates="customer"
    )
    # All addresses registered by this customer.


class Address(BaseModel):
    __tablename__ = "addresses"

    customer: Mapped["Customer"] = relationship("Customer", back_populates="addresses")
    # The customer this address belongs to.
```

## 9. Declare indexes explicitly

Add indexes for columns used in lookups or filters. Do not rely on implicit indexing
beyond the primary key.

```python
from sqlalchemy import Index


class Customer(BaseModel):
    __tablename__ = "customers"

    __table_args__ = (
        Index("idx_customers_email", "email", unique=True),
        Index(
            "idx_customers_identity_provider_id", "identity_provider_id", unique=True
        ),
    )
```

## 10. Keep models free of business logic

Models must only describe structure. Validation, computation, and state transitions
belong in the service layer.

```python
# wrong — business logic in the model
class Order(BaseModel):
    def cancel(self) -> None:
        if self.status == "shipped":
            raise ValueError("Cannot cancel a shipped order")
        self.status = "cancelled"


# correct — model describes structure only
class Order(BaseModel):
    __tablename__ = "orders"

    status: Mapped[str] = mapped_column(String(50), nullable=False)
    # Current lifecycle status of the order (e.g. pending, confirmed, shipped).
```

