from app.shared.audit_log.port import AuditPort
from app.shared.audit_log.schemas import AuditRecord


class NoOpAuditRepository(AuditPort):
    """Audit port implementation that discards all records silently.

    Use in tests and local development environments where MongoDB is not
    available. Never use in production.
    """

    def record(self, entry: AuditRecord) -> None:
        """Discard the audit record without writing it anywhere.

        Args:
            entry: The audit record to discard.
        """
