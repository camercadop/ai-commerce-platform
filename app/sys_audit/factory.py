import os

from app.shared.audit_log import AuditPort, MongoSettings, NoOpAuditRepository
from app.sys_audit.repository import MongoAuditRepository


def resolve_audit_repo() -> AuditPort:
    """Return a configured AuditPort based on the environment.

    Instantiates a MongoAuditRepository when all MONGO_* environment
    variables are present; falls back to NoOpAuditRepository otherwise.

    Returns:
        A ready-to-use AuditPort instance.
    """
    required = (
        "MONGO_USERNAME",
        "MONGO_PASSWORD",
        "MONGO_HOST",
        "MONGO_PORT",
        "MONGO_DATABASE",
    )
    if all(os.environ.get(k) for k in required):
        return MongoAuditRepository(MongoSettings())  # type: ignore[call-arg]
    return NoOpAuditRepository()
