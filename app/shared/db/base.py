from datetime import UTC, datetime

from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class BaseModel(DeclarativeBase):
    """Declarative base for all SQLAlchemy ORM models.

    Every domain model must inherit from this base. Each domain maintains
    its own Alembic migration environment — never share migration histories
    across domains (ADR-001).
    """

    __abstract__ = True


class TimestampMixin:
    """Mixin that provides created_at and updated_at audit timestamp columns.

    Inherit from this mixin to track when a record was created and last updated.
    Timestamps are set by the database server, not the application clock.
    """

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


class SoftDeleteMixin:
    """Mixin that provides soft delete support via a deleted_at timestamp.

    Records are never physically removed. Setting deleted_at marks the record
    as deleted. A null value means the record is active.
    """

    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
    )
    # Timestamp when this record was soft-deleted. Null means active.

    @property
    def is_deleted(self) -> bool:
        """Return True if this record has been soft-deleted."""
        return self.deleted_at is not None

    def soft_delete(self) -> None:
        """Mark this record as deleted by setting deleted_at to the current UTC time."""
        self.deleted_at = datetime.now(UTC)

    def restore(self) -> None:
        """Restore a soft-deleted record by clearing deleted_at."""
        self.deleted_at = None
