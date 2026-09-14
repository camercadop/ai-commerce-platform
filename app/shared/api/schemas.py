from typing import Any

from fastapi import Request
from pydantic import BaseModel, ConfigDict


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


class RequestContext(BaseModel):
    """Typed wrapper for extracting and coercing values from a FastAPI Request.

    Subclass this to declare the path params, query params, or headers your
    operation callable needs. Call model_validate({'request': request}) to get
    a fully coerced and validated instance.

    Subclasses should override path_params, query_params, or headers with
    typed nested models to get automatic coercion from the raw request strings.

    Example:
        class ProductPathParams(BaseModel):
            product_id: uuid.UUID

        class VariantContext(RequestContext):
            path_params: ProductPathParams

        ctx = VariantContext.model_validate({'request': request})
        product_id = ctx.path_params.product_id
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    request: Request

    @property
    def path_params(self) -> dict[str, Any]:
        """Return raw path params from the request as a plain dict."""
        return dict(self.request.path_params)

    @property
    def query_params(self) -> dict[str, Any]:
        """Return raw query params from the request as a plain dict."""
        return dict(self.request.query_params)

    @property
    def headers(self) -> dict[str, Any]:
        """Return raw headers from the request as a plain dict."""
        return dict(self.request.headers)
