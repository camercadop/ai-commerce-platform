import logging

from fastapi import FastAPI

from app.identity.container import IdentityContainer
from app.identity.routes import (
    _audit_dependency,
    _auth_dependency,
    _db_dependency,
    address_router,
    customer_router,
    register_exception_handlers,
)
from app.identity.service import _load_preferences_config
from app.shared.api import (
    register_exception_handlers as register_shared_exception_handlers,
)
from app.shared.audit_log import MongoSettings, NoOpAuditRepository
from app.shared.auth import AuthSettings, JWTValidator, build_auth_dependency
from app.shared.db import DatabaseSettings, build_session_factory, make_get_db
from app.sys_audit import MongoAuditRepository

logger = logging.getLogger(__name__)


def create_app(
    db_settings: DatabaseSettings,
    auth_settings: AuthSettings,
    mongo_settings: MongoSettings | None = None,
) -> FastAPI:
    """Create and configure the identity FastAPI application.

    Wires the IdentityContainer with the audit repository singleton.
    The db session remains under FastAPI's request-scoped control.
    Settings are injected rather than read from the environment directly to
    allow overriding in tests.

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

    session_factory = build_session_factory(
        db_settings.database_base_url + "/commerce_identity"
    )
    validator = JWTValidator(
        secret=auth_settings.auth_jwt_secret,
        algorithm=auth_settings.auth_jwt_algorithm,
        audience=auth_settings.auth_jwt_audience,
    )
    get_current_user = build_auth_dependency(validator)
    audit_repo = (
        MongoAuditRepository(mongo_settings)
        if mongo_settings
        else NoOpAuditRepository()
    )

    container = IdentityContainer()
    container.audit.override(audit_repo)
    app.state.container = container

    app.dependency_overrides[_db_dependency] = make_get_db(session_factory)
    app.dependency_overrides[_auth_dependency] = get_current_user
    app.dependency_overrides[_audit_dependency] = lambda: container.audit()

    register_shared_exception_handlers(app)
    register_exception_handlers(app)

    app.include_router(customer_router)
    app.include_router(address_router)

    @app.get("/api/v1/identity/health")
    def health() -> dict[str, str]:
        """Return service health status."""
        return {"status": "ok"}

    _load_preferences_config()
    logger.info("Identity service application created")
    return app
