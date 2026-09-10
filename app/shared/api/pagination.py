import base64
import json
import uuid
from datetime import datetime
from typing import Any

from app.shared.api.schemas import PaginatedResponse, PaginationMeta


def encode_cursor(created_at: datetime, record_id: uuid.UUID) -> str:
    """Encode a keyset cursor as a base64 JSON string.

    Args:
        created_at: The created_at timestamp of the last record in the page.
        record_id: The id of the last record in the page.
    """
    payload = {"created_at": created_at.isoformat(), "id": str(record_id)}
    return base64.urlsafe_b64encode(json.dumps(payload).encode()).decode()


def decode_cursor(cursor: str) -> tuple[datetime, uuid.UUID]:
    """Decode a base64 JSON cursor into (created_at, id).

    Args:
        cursor: An opaque cursor string produced by encode_cursor.
    """
    payload = json.loads(base64.urlsafe_b64decode(cursor.encode()))
    return datetime.fromisoformat(payload["created_at"]), uuid.UUID(payload["id"])


def paginate(
    rows: list[Any],
    page_size: int,
    to_response: Any,
    get_cursor_fields: Any,
) -> PaginatedResponse[Any]:
    """Build a PaginatedResponse from a limit+1 query result.

    Callers must query page_size + 1 rows. This function trims the extra row,
    determines has_more, and encodes the next cursor.

    Args:
        rows: Results from a limit+1 query.
        page_size: The declared page size for this endpoint.
        to_response: Callable that maps a row to its response schema.
        get_cursor_fields: Callable(row) -> (created_at, id) for cursor encoding.

    Example:
        rows = repo.list_page(limit=PAGE_SIZE + 1, cursor=decoded_cursor)
        return paginate(
            rows=rows,
            page_size=PAGE_SIZE,
            to_response=lambda r: ProductResponse.model_validate(
                r, from_attributes=True
            ),
            get_cursor_fields=lambda r: (r.created_at, r.id),
        )
    """
    has_more = len(rows) > page_size
    page = rows[:page_size]
    next_cursor: str | None = None
    if has_more:
        created_at, record_id = get_cursor_fields(page[-1])
        next_cursor = encode_cursor(created_at, record_id)
    return PaginatedResponse(
        data=[to_response(r) for r in page],
        pagination=PaginationMeta(next_cursor=next_cursor, has_more=has_more),
    )
