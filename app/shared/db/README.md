# db

Provides the SQLAlchemy engine and session factory, the declarative ORM base, shared
model mixins, a generic repository, and the FastAPI session dependency. Each domain
maintains its own Alembic migration environment and must never share migration history
with another domain (ADR-001).

## Package layout

```
db/
├── __init__.py     # Package entry point
├── base.py         # ORM declarative base and model mixins
├── repository.py   # Generic CRUD repository
├── session.py      # Database session and engine factory
└── settings.py     # Database configuration
```

## Public API

### Models

| Symbol | Description |
| --- | --- |
| `BaseModel` | SQLAlchemy `DeclarativeBase` all domain models must inherit from |
| `TimestampMixin` | Adds `created_at` and `updated_at` columns, set by the database server |
| `SoftDeleteMixin` | Adds `deleted_at`; provides `is_deleted`, `soft_delete()`, and `restore()` |

### Repository

| Symbol | Description |
| --- | --- |
| `BaseRepository[T]` | Generic repository with `get_by_id`, `list_page`, `create`, `update`, `delete` |

Subclass `BaseRepository` and set `model_class` to add domain-specific query methods.
`delete()` soft-deletes automatically when the model inherits `SoftDeleteMixin`;
otherwise it issues a hard delete.

`list_page()` applies keyset pagination on `(created_at, id)` and excludes
soft-deleted rows automatically.

```python
from app.shared.db import BaseModel, BaseRepository, SoftDeleteMixin, TimestampMixin


class Product(BaseModel, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "products"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str]


class ProductRepository(BaseRepository[Product]):
    model_class = Product

    def get_by_name(self, name: str) -> Product | None:
        return self.session.execute(
            select(Product).where(Product.name == name, Product.deleted_at.is_(None))
        ).scalar_one_or_none()
```

### Session

| Symbol | Description |
| --- | --- |
| `build_session_factory(database_url)` | Creates a `sessionmaker` bound to the given URL; call once at startup |
| `make_get_db(session_factory)` | Returns a zero-argument FastAPI dependency that yields a scoped `Session` |
| `get_db(session_factory)` | Generator that yields a session directly; use when `Depends` is not available |

### Configuration

| Key | Description | Default |
| --- | --- | --- |
| `DATABASE_BASE_URL` | SQLAlchemy connection string base URL | required |
