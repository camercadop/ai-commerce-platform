from typing import Any

from pydantic import BaseModel


class ErrorDetail(BaseModel):
    """Structured error payload included in all error responses."""

    code: str
    message: str


class DataResponse[T](BaseModel):
    """Envelope for a single-resource success response.

    Use this for all non-paginated responses that return a single object.
    Do not use for collections — use PaginatedResponse instead.
    """

    data: T


class PaginationMeta(BaseModel):
    """Cursor-based pagination metadata attached to collection responses."""

    next_cursor: str | None
    has_more: bool


class PaginatedResponse[T](BaseModel):
    """Envelope for a paginated collection response.

    Use this for all collection endpoints. Always declare a page size limit
    and populate has_more so consumers can determine whether more results exist.
    """

    data: list[T]
    pagination: PaginationMeta


class ErrorResponse(BaseModel):
    """Envelope for all error responses.

    The code field is a screaming snake case string that uniquely identifies
    the failure mode. Consumers must use code, not message, for programmatic
    error handling.
    """

    error: ErrorDetail


def error_response(code: str, message: str) -> dict[str, Any]:
    """Build a serialized error response dict ready for use in JSONResponse.

    Use this in exception handlers to produce a consistent error envelope
    without instantiating ErrorResponse manually.
    """
    return ErrorResponse(error=ErrorDetail(code=code, message=message)).model_dump()
