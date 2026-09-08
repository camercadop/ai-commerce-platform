from app.shared.api import (
    DataResponse,
    ErrorResponse,
    PaginatedResponse,
    PaginationMeta,
    error_response,
)


def test_data_response_wraps_payload() -> None:
    response = DataResponse(data={"id": "123", "name": "Headphones"})

    assert response.data == {"id": "123", "name": "Headphones"}


def test_paginated_response_structure() -> None:
    response = PaginatedResponse(
        data=[{"id": "1"}, {"id": "2"}],
        pagination=PaginationMeta(next_cursor="abc", has_more=True),
    )

    assert len(response.data) == 2
    assert response.pagination.next_cursor == "abc"
    assert response.pagination.has_more is True


def test_paginated_response_last_page() -> None:
    response = PaginatedResponse(
        data=[{"id": "1"}],
        pagination=PaginationMeta(next_cursor=None, has_more=False),
    )

    assert response.pagination.next_cursor is None
    assert response.pagination.has_more is False


def test_error_response_structure() -> None:
    response = ErrorResponse.model_validate(
        {"error": {"code": "PRODUCT_NOT_FOUND", "message": "Product not found: 123"}}
    )

    assert response.error.code == "PRODUCT_NOT_FOUND"
    assert response.error.message == "Product not found: 123"


def test_error_response_helper() -> None:
    result = error_response("PRODUCT_NOT_FOUND", "Product not found: 123")

    assert result == {
        "error": {"code": "PRODUCT_NOT_FOUND", "message": "Product not found: 123"}
    }
