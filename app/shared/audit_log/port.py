from abc import ABC, abstractmethod

from app.shared.audit_log.schemas import AuditRecord


class AuditPort(ABC):
    """Abstract port for writing audit records.

    All concrete implementations must live outside app/shared/ (e.g. app/sys_audit/).
    Domain code must never depend on a concrete implementation directly (ADR-004).

    Implementations are responsible for translating AuditRecord into the
    underlying store format. No store-specific SDK or data format may appear
    in domain code.
    """

    @abstractmethod
    def record(self, entry: AuditRecord) -> None:
        """Write an audit record to the audit store.

        Implementations must treat this as best-effort — failures must be
        logged as warnings and must never propagate exceptions to the caller.
        The domain transaction must never be rolled back due to an audit failure.

        Args:
            entry: The audit record to persist.
        """
