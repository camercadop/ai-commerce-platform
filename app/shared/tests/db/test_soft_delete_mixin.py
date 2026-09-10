from datetime import UTC, datetime

from app.shared.db.base import SoftDeleteMixin


class _Model(SoftDeleteMixin):
    """Minimal concrete class to exercise SoftDeleteMixin in isolation."""


def test_is_deleted_false_when_deleted_at_is_none() -> None:
    model = _Model()
    model.deleted_at = None

    assert model.is_deleted is False


def test_is_deleted_true_after_soft_delete() -> None:
    model = _Model()
    model.deleted_at = None

    model.soft_delete()

    assert model.is_deleted is True


def test_soft_delete_sets_deleted_at_to_utc_now() -> None:
    model = _Model()
    model.deleted_at = None
    before = datetime.now(UTC)

    model.soft_delete()

    assert model.deleted_at is not None
    assert model.deleted_at >= before


def test_restore_clears_deleted_at() -> None:
    model = _Model()
    model.soft_delete()

    model.restore()

    assert model.deleted_at is None
    assert model.is_deleted is False
