import logging

from fastapi import FastAPI

from app.identity.routes import (
    _auth_dependency,
    _db_dependency,
    address_router,
    customer_router,
    register_exception_handlers,
)
from app.shared.auth import AuthSettings, JWTValidator, build_auth_dependency
from app.shared.db import DatabaseSettings, build_session_factory, make_get_db

logger = logging.getLogger(__name__)


def _register_middlewares(app: FastAPI) -> None:
    """Register all middlewares on the FastAPI app.

    Centralises middleware wiring so that create_app stays focused on
    application bootstrap. Add new middlewares here rather than in create_app.

    Args:
        app: The FastAPI application instance.
    """


def create_app(
    db_settings: DatabaseSettings,
    auth_settings: AuthSettings,
) -> FastAPI:
    """Create and configure the identity FastAPI application.

    Wires the session factory, auth dependency, routers, and exception handlers.
    Settings are injected rather than read from the environment directly to
    allow overriding in tests.

    Args:
        db_settings: Database connection settings.
        auth_settings: JWT validation settings.

    Returns:
        A fully configured FastAPI application instance.
    """
    app = FastAPI(title="Identity Service")

    session_factory = build_session_factory(db_settings.database_url)
    validator = JWTValidator(
        public_key=auth_settings.auth_jwt_public_key,
        algorithm=auth_settings.auth_jwt_algorithm,
        audience=auth_settings.auth_jwt_audience,
    )
    get_current_user = build_auth_dependency(validator)

    app.dependency_overrides[_db_dependency] = make_get_db(session_factory)
    app.dependency_overrides[_auth_dependency] = get_current_user

    _register_middlewares(app)
    register_exception_handlers(app)

    app.include_router(customer_router)
    app.include_router(address_router)

    @app.get("/health")
    def health() -> dict[str, str]:
        """Return service health status."""
        return {"status": "ok"}

    logger.info("Identity service application created")
    return app
