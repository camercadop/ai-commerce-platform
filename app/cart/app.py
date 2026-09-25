import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.cart.adapters import StubCatalogPort, StubInventoryPort
from app.cart.ports import CatalogPort
from app.cart.routes import (
    _audit_dependency,
    _auth_dependency,
    _broker_dependency,
    _catalog_dependency,
    _db_dependency,
    _inventory_dependency,
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
    catalog_port: CatalogPort | None = None,
) -> FastAPI:
    """Create and configure the cart FastAPI application.

    Wires the session factory, auth dependency, audit repository, message
    broker, catalog port, routers, and exception handlers. Settings are
    injected rather than read from the environment directly to allow
    overriding in tests.

    Args:
        db_settings: Database connection settings for the cart database.
        auth_settings: JWT validation settings.
        broker: Message broker used to publish cart domain events. When
            None, resolved automatically from the environment via
            `resolve_broker()`.
        audit_repo: AuditPort used to persist audit records. When None,
            resolved automatically from the environment via
            `resolve_audit_repo()`.
        catalog_port: CatalogPort implementation for reading variant prices.
            When None, a StubCatalogPort is used — suitable for tests and
            local development without a running catalog database.

    Returns:
        A fully configured FastAPI application instance.
    """
    session_factory = build_session_factory(
        db_settings.database_base_url + "/commerce_cart"
    )
    validator = JWTValidator(
        secret=auth_settings.auth_jwt_secret,
        algorithm=auth_settings.auth_jwt_algorithm,
        audience=auth_settings.auth_jwt_audience,
    )
    get_current_user = build_auth_dependency(validator)
    resolved_audit = audit_repo if audit_repo is not None else resolve_audit_repo()
    resolved_broker = broker if broker is not None else resolve_broker()
    resolved_catalog = catalog_port if catalog_port is not None else StubCatalogPort()

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncGenerator[None]:
        resolved_broker.start()
        yield
        resolved_broker.stop()

    app = FastAPI(title="Cart Service", lifespan=lifespan)

    app.dependency_overrides[_db_dependency] = make_get_db(session_factory)
    app.dependency_overrides[_auth_dependency] = get_current_user
    app.dependency_overrides[_audit_dependency] = lambda: resolved_audit
    app.dependency_overrides[_broker_dependency] = lambda: resolved_broker
    app.dependency_overrides[_catalog_dependency] = lambda: resolved_catalog
    app.dependency_overrides[_inventory_dependency] = lambda: StubInventoryPort()

    register_shared_exception_handlers(app)
    register_exception_handlers(app)
    app.include_router(router)

    @app.get("/api/v1/cart/health")
    def health() -> dict[str, str]:
        """Return service health status."""
        return {"status": "ok"}

    logger.info("Cart service application created")
    return app
