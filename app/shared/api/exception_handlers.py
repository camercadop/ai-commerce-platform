import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.shared.api.schemas import error_response
from app.shared.exceptions import ResourceAlreadyExists, ResourceNotFound

logger = logging.getLogger(__name__)


def register_exception_handlers(app: FastAPI) -> None:
    """Register shared exception handlers for ResourceNotFound and
    ResourceAlreadyExists.

    Must be called before domain-specific handler registration so that domain
    subclasses are caught by the more specific domain handlers when needed.

    Args:
        app: The FastAPI application instance.
    """

    @app.exception_handler(ResourceNotFound)
    def handle_not_found(request: Request, exc: ResourceNotFound) -> JSONResponse:
        logger.warning(
            "resource_not_found resource=%s id=%s", exc.resource_name, exc.resource_id
        )
        return JSONResponse(status_code=404, content=error_response(exc.code, str(exc)))

    @app.exception_handler(ResourceAlreadyExists)
    def handle_already_exists(
        request: Request, exc: ResourceAlreadyExists
    ) -> JSONResponse:
        logger.warning(
            "resource_already_exists resource=%s identifier=%s",
            exc.resource_name,
            exc.identifier,
        )
        return JSONResponse(status_code=409, content=error_response(exc.code, str(exc)))
