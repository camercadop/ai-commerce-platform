import logging

from fastapi import FastAPI

from app.identity.routes import (
    _audit_dependency,
    _auth_dependency,
    _db_dependency,
    address_router,
    build_customer_router,
    register_exception_handlers,
)
from app.identity.service import _load_preferences_config
from app.shared.audit_log import MongoSettings, NoOpAuditRepository
from app.shared.auth import AuthSettings, JWTValidator, build_auth_dependency
from app.shared.db import DatabaseSettings, build_session_factory, make_get_db
from app.sys_audit import MongoAuditRepository

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
    mongo_settings: MongoSettings | None = None,
) -> FastAPI:
    """Create and configure the identity FastAPI application.

    Wires the session factory, auth dependency, audit repository, routers,
    and exception handlers. Settings are injected rather than read from the
    environment directly to allow overriding in tests.

    Args:
        db_settings: Database connection settings.
        auth_settings: JWT validation settings.
        mongo_settings: MongoDB connection settings for the audit log. When
            None, a no-op audit repository is used — suitable for tests and
            local development without MongoDB.

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
    audit_repo = (
        MongoAuditRepository(mongo_settings)
        if mongo_settings
        else NoOpAuditRepository()
    )

    app.dependency_overrides[_db_dependency] = make_get_db(session_factory)
    app.dependency_overrides[_auth_dependency] = get_current_user
    app.dependency_overrides[_audit_dependency] = lambda: audit_repo

    _register_middlewares(app)
    register_exception_handlers(app)

    app.include_router(build_customer_router(audit_repo))
    app.include_router(address_router)

    @app.get("/health")
    def health() -> dict[str, str]:
        """Return service health status."""
        return {"status": "ok"}

    _load_preferences_config()
    logger.info("Identity service application created")
    return app
