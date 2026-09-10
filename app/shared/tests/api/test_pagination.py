import uuid
from datetime import datetime, timezone

import pytest

from app.shared.api.pagination import decode_cursor, encode_cursor, paginate


def test_encode_decode_cursor_round_trip() -> None:
    created_at = datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
    record_id = uuid.uuid4()

    cursor = encode_cursor(created_at, record_id)
    decoded_at, decoded_id = decode_cursor(cursor)

    assert decoded_at == created_at
    assert decoded_id == record_id


def test_encode_cursor_produces_valid_base64_json(subtests: pytest.Subtests) -> None:
    import base64
    import json

    created_at = datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
    record_id = uuid.UUID("12345678-1234-5678-1234-567812345678")

    cursor = encode_cursor(created_at, record_id)
    payload = json.loads(base64.urlsafe_b64decode(cursor.encode()))

    with subtests.test("created_at field"):
        assert payload["created_at"] == created_at.isoformat()

    with subtests.test("id field"):
        assert payload["id"] == str(record_id)


def _make_row(created_at: datetime) -> object:
    class Row:
        id = uuid.uuid4()

    row = Row()
    row.created_at = created_at  # type: ignore[attr-defined]
    return row


def test_paginate_has_more_true() -> None:
    page_size = 2
    rows = [
        _make_row(datetime(2024, 1, i + 1, tzinfo=timezone.utc))
        for i in range(page_size + 1)
    ]

    result = paginate(
        rows=rows,
        page_size=page_size,
        to_response=lambda r: r,
        get_cursor_fields=lambda r: (r.created_at, r.id),
    )

    assert result.pagination.has_more is True
    assert result.pagination.next_cursor is not None
    assert len(result.data) == page_size


def test_paginate_has_more_false() -> None:
    page_size = 2
    rows = [
        _make_row(datetime(2024, 1, i + 1, tzinfo=timezone.utc))
        for i in range(page_size)
    ]

    result = paginate(
        rows=rows,
        page_size=page_size,
        to_response=lambda r: r,
        get_cursor_fields=lambda r: (r.created_at, r.id),
    )

    assert result.pagination.has_more is False
    assert result.pagination.next_cursor is None
    assert len(result.data) == page_size
