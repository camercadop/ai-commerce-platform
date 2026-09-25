import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

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
from app.shared.api import (
    register_exception_handlers as register_shared_exception_handlers,
)
from app.shared.audit_log import AuditPort
from app.shared.auth import AuthSettings, JWTValidator, build_auth_dependency
from app.shared.db import DatabaseSettings, build_session_factory, make_get_db
from app.shared.events import MessageBroker
from app.sys_audit import resolve_audit_repo
from app.sys_eventbus import resolve_broker

logger = logging.getLogger(__name__)


def create_app(
    db_settings: DatabaseSettings,
    auth_settings: AuthSettings,
    broker: MessageBroker | None = None,
    audit_repo: AuditPort | None = None,
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
            None, resolved automatically from the environment via
            `resolve_broker()`.
        audit_repo: AuditPort used to persist audit records. When None,
            resolved automatically from the environment via
            `resolve_audit_repo()`.
        cart_port: CartPort implementation for reading cart data during
            checkout. When None, a stub is used — suitable for tests and
            local development without a running cart service.
        adjustment_rules_port: AdjustmentRulesPort implementation for
            evaluating order adjustment rules. When None, a stub is used
            that returns no adjustments.

    Returns:
        A fully configured FastAPI application instance.
    """
    session_factory = build_session_factory(
        db_settings.database_base_url + "/commerce_orders"
    )
    validator = JWTValidator(
        secret=auth_settings.auth_jwt_secret,
        algorithm=auth_settings.auth_jwt_algorithm,
        audience=auth_settings.auth_jwt_audience,
    )
    get_current_user = build_auth_dependency(validator)
    resolved_audit = audit_repo if audit_repo is not None else resolve_audit_repo()
    resolved_broker = broker if broker is not None else resolve_broker()
    resolved_cart = cart_port if cart_port is not None else StubCartPort()
    resolved_adjustment_rules = (
        adjustment_rules_port
        if adjustment_rules_port is not None
        else StubAdjustmentRulesPort()
    )

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncGenerator[None]:
        resolved_broker.start()
        yield
        resolved_broker.stop()

    app = FastAPI(title="Orders Service", lifespan=lifespan)

    app.dependency_overrides[_db_dependency] = make_get_db(session_factory)
    app.dependency_overrides[_auth_dependency] = get_current_user
    app.dependency_overrides[_audit_dependency] = lambda: resolved_audit
    app.dependency_overrides[_broker_dependency] = lambda: resolved_broker
    app.dependency_overrides[_cart_dependency] = lambda: resolved_cart
    app.dependency_overrides[_adjustment_rules_dependency] = lambda: (
        resolved_adjustment_rules
    )

    register_shared_exception_handlers(app)
    register_exception_handlers(app)
    app.include_router(router)

    @app.get("/api/v1/orders/health")
    def health() -> dict[str, str]:
        """Return service health status."""
        return {"status": "ok"}

    logger.info("Orders service application created")
    return app
