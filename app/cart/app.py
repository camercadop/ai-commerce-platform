import logging

from fastapi import FastAPI

from app.cart.routes import (
    _audit_dependency,
    _auth_dependency,
    _broker_dependency,
    _db_dependency,
    register_exception_handlers,
    router,
)
from app.shared.audit_log import MongoSettings, NoOpAuditRepository
from app.shared.auth import AuthSettings, JWTValidator, build_auth_dependency
from app.shared.db import DatabaseSettings, build_session_factory, make_get_db
from app.shared.events import MessageBroker, NoOpMessageBroker
from app.sys_audit import MongoAuditRepository

logger = logging.getLogger(__name__)


def create_app(
    db_settings: DatabaseSettings,
    auth_settings: AuthSettings,
    broker: MessageBroker | None = None,
    mongo_settings: MongoSettings | None = None,
) -> FastAPI:
    """Create and configure the cart FastAPI application.

    Wires the session factory, auth dependency, audit repository, message
    broker, routers, and exception handlers. Settings are injected rather
    than read from the environment directly to allow overriding in tests.

    Args:
        db_settings: Database connection settings.
        auth_settings: JWT validation settings.
        broker: Message broker used to publish cart domain events. When
            None, a no-op broker is used — suitable for tests and local
            development without a running broker.
        mongo_settings: MongoDB connection settings for the audit log. When
            None, a no-op audit repository is used — suitable for tests and
            local development without MongoDB.

    Returns:
        A fully configured FastAPI application instance.
    """
    app = FastAPI(title="Cart Service")

    session_factory = build_session_factory(
        db_settings.database_base_url + "/commerce_cart"
    )
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
    resolved_broker = broker if broker is not None else NoOpMessageBroker()

    app.dependency_overrides[_db_dependency] = make_get_db(session_factory)
    app.dependency_overrides[_auth_dependency] = get_current_user
    app.dependency_overrides[_audit_dependency] = lambda: audit_repo
    app.dependency_overrides[_broker_dependency] = lambda: resolved_broker

    register_exception_handlers(app)
    app.include_router(router)

    @app.get("/health")
    def health() -> dict[str, str]:
        """Return service health status."""
        return {"status": "ok"}

    logger.info("Cart service application created")
    return app
