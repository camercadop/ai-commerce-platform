import logging

from fastapi import FastAPI

from app.catalog.container import CatalogContainer
from app.catalog.routes import (
    _audit_dependency,
    _auth_dependency,
    _broker_dependency,
    _db_dependency,
    attribute_router,
    brand_router,
    category_router,
    product_router,
    register_exception_handlers,
    variant_router,
)
from app.shared.api import (
    register_exception_handlers as register_shared_exception_handlers,
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
    """Create and configure the catalog FastAPI application.

    Wires the CatalogContainer with the audit repository and message broker
    singletons. The db session remains under FastAPI's request-scoped control.
    Settings are injected rather than read from the environment directly to
    allow overriding in tests.

    Args:
        db_settings: Database connection settings.
        auth_settings: JWT validation settings.
        broker: Message broker used to publish catalog domain events. When
            None, a no-op broker is used — suitable for tests and local
            development without a running broker.
        mongo_settings: MongoDB connection settings for the audit log. When
            None, a no-op audit repository is used — suitable for tests and
            local development without MongoDB.

    Returns:
        A fully configured FastAPI application instance.
    """
    app = FastAPI(title="Catalog Service")

    session_factory = build_session_factory(
        db_settings.database_base_url + "/commerce_catalog"
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

    container = CatalogContainer()
    container.audit.override(audit_repo)
    container.broker.override(resolved_broker)
    app.state.container = container

    app.dependency_overrides[_db_dependency] = make_get_db(session_factory)
    app.dependency_overrides[_auth_dependency] = get_current_user
    app.dependency_overrides[_audit_dependency] = lambda: container.audit()
    app.dependency_overrides[_broker_dependency] = lambda: container.broker()

    register_shared_exception_handlers(app)
    register_exception_handlers(app)

    app.include_router(category_router)
    app.include_router(brand_router)
    app.include_router(product_router)
    app.include_router(variant_router)
    app.include_router(attribute_router)

    @app.get("/health")
    def health() -> dict[str, str]:
        """Return service health status."""
        return {"status": "ok"}

    logger.info("Catalog service application created")
    return app
