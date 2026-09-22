from dependency_injector import containers, providers

from app.shared.audit_log import AuditPort, NoOpAuditRepository


class IdentityContainer(containers.DeclarativeContainer):
    """Dependency container for the identity domain.

    Manages infrastructure singletons that are shared across all requests.
    audit is initialized once on first use and reused for the lifetime of
    the application.

    Repository and service instances are request-scoped and constructed by
    FastAPI dependency functions in routes.py, which receive the db session
    from FastAPI and pull audit from this container.

    Wire this container to the routes module at application startup via
    container.wire(modules=[routes_module]).
    """

    audit: providers.Singleton[AuditPort] = providers.Singleton(NoOpAuditRepository)
