import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.shared.db.base import BaseModel, SoftDeleteMixin


class BaseRepository[T: BaseModel]:
    """Generic repository providing common CRUD operations for a SQLAlchemy model.

    Subclasses must set the model_class attribute to the concrete model type.
    Soft delete is supported automatically when the model inherits SoftDeleteMixin.
    Use a domain-specific subclass to add query methods beyond the base interface.
    """

    model_class: type[T]

    def __init__(self, session: Session) -> None:
        """Initialize the repository with an active database session.

        Args:
            session: The SQLAlchemy session scoped to the current request.
        """
        self.session = session

    def get_by_id(self, record_id: uuid.UUID) -> T | None:
        """Return the record with the given id, or None if not found or soft-deleted.

        Args:
            record_id: The UUID primary key of the record.
        """
        stmt = select(self.model_class).where(self.model_class.id == record_id)  # type: ignore[attr-defined]
        if issubclass(self.model_class, SoftDeleteMixin):
            stmt = stmt.where(self.model_class.deleted_at.is_(None))
        return self.session.execute(stmt).scalar_one_or_none()

    def list_page(
        self,
        *filters: Any,
        limit: int,
        cursor: tuple[datetime, uuid.UUID] | None = None,
    ) -> list[T]:
        """Return a keyset-paginated list of records matching the given filters.

        Results are ordered by (created_at, id) ascending. Soft-deleted records
        are excluded automatically when the model inherits SoftDeleteMixin.

        Args:
            *filters: SQLAlchemy column expressions to filter by.
            limit: Maximum number of records to return.
            cursor: Exclusive lower bound as (created_at, id) for keyset pagination.
        """
        model = self.model_class
        stmt = (
            select(model)
            .where(*filters)
            .order_by(model.created_at, model.id)  # type: ignore[attr-defined]
            .limit(limit)
        )
        if issubclass(model, SoftDeleteMixin):
            stmt = stmt.where(model.deleted_at.is_(None))
        if cursor is not None:
            cursor_at, cursor_id = cursor
            stmt = stmt.where(
                (model.created_at > cursor_at)  # type: ignore[attr-defined]
                | ((model.created_at == cursor_at) & (model.id > cursor_id))  # type: ignore[attr-defined]
            )
        return list(self.session.execute(stmt).scalars().all())

    def create(self, **kwargs: Any) -> T:
        """Create and persist a new record with the given field values.

        Args:
            **kwargs: Column values for the new record.
        """
        record = self.model_class(**kwargs)
        self.session.add(record)
        self.session.flush()
        return record

    def update(self, record: T, data: dict[str, Any]) -> T:
        """Apply a partial update to an existing record.

        Only keys present in data are updated. The caller is responsible for
        passing a record that was loaded in the current session.

        Args:
            record: The model instance to update.
            data: A dict of field names to new values.
        """
        for key, value in data.items():
            setattr(record, key, value)
        self.session.flush()
        return record

    def delete(self, record: T) -> None:
        """Soft-delete a record if the model supports it, otherwise hard-delete.

        For models with SoftDeleteMixin, sets deleted_at to the current UTC time.
        For models without it, removes the row from the database.

        Args:
            record: The model instance to delete.
        """
        if isinstance(record, SoftDeleteMixin):
            record.soft_delete()
        else:
            self.session.delete(record)
        self.session.flush()
