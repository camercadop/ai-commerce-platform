import logging

from fastapi import FastAPI

from app.orders.adapters import StubAdjustmentRulesPort, StubCartPort
from app.orders.ports import AdjustmentRulesPort, CartPort
from app.orders.routes import (
    _adjustment_rules_dependency,
    _audit_dependency,
    _auth_dependency,
    _broker_dependency,
    _cart_dependency,
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
    cart_port: CartPort | None = None,
    adjustment_rules_port: AdjustmentRulesPort | None = None,
) -> FastAPI:
    """Create and configure the orders FastAPI application.

    Wires the session factory, auth dependency, audit repository, message
    broker, routers, and exception handlers. Settings are injected rather
    than read from the environment directly to allow overriding in tests.

    Args:
        db_settings: Database connection settings.
        auth_settings: JWT validation settings.
        broker: Message broker used to publish orders domain events. When
            None, a no-op broker is used — suitable for tests and local
            development without a running broker.
        mongo_settings: MongoDB connection settings for the audit log. When
            None, a no-op audit repository is used — suitable for tests and
            local development without MongoDB.
        cart_port: CartPort implementation for reading cart data during
            checkout. When None, a stub is used — suitable for tests and
            local development without a running cart service.
        adjustment_rules_port: AdjustmentRulesPort implementation for
            evaluating order adjustment rules. When None, a stub is used
            that returns no adjustments.

    Returns:
        A fully configured FastAPI application instance.
    """
    app = FastAPI(title="Orders Service")

    session_factory = build_session_factory(
        db_settings.database_base_url + "/commerce_orders"
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
    resolved_cart = cart_port if cart_port is not None else StubCartPort()
    resolved_adjustment_rules = (
        adjustment_rules_port
        if adjustment_rules_port is not None
        else StubAdjustmentRulesPort()
    )

    app.dependency_overrides[_db_dependency] = make_get_db(session_factory)
    app.dependency_overrides[_auth_dependency] = get_current_user
    app.dependency_overrides[_audit_dependency] = lambda: audit_repo
    app.dependency_overrides[_broker_dependency] = lambda: resolved_broker
    app.dependency_overrides[_cart_dependency] = lambda: resolved_cart
    app.dependency_overrides[_adjustment_rules_dependency] = lambda: (
        resolved_adjustment_rules
    )

    register_exception_handlers(app)
    app.include_router(router)

    @app.get("/health")
    def health() -> dict[str, str]:
        """Return service health status."""
        return {"status": "ok"}

    logger.info("Orders service application created")
    return app
