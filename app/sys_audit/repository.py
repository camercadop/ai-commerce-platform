import logging

from pymongo import MongoClient
from pymongo.errors import PyMongoError

from app.shared.audit_log import AuditPort, AuditRecord, MongoSettings

logger = logging.getLogger(__name__)

_COLLECTION = "audit_records"


class MongoAuditRepository(AuditPort):
    """Writes audit records to a MongoDB collection.

    Each record is inserted as an immutable document. Failures are logged
    as warnings and never propagate to the caller — the domain transaction
    must never be rolled back due to an audit write failure (ADR-013).
    """

    def __init__(self, settings: MongoSettings) -> None:
        """Initialize the repository with a MongoDB connection.

        Args:
            settings: MongoDB connection settings.
        """
        self._client: MongoClient[dict] = MongoClient(settings.uri)  # type: ignore[type-arg]
        self._collection = self._client[settings.mongo_database][_COLLECTION]

    def record(self, entry: AuditRecord) -> None:
        """Insert an audit record into the MongoDB collection.

        Failures are caught and logged as warnings. The caller is never
        notified of a failure — audit writes are best-effort.

        Args:
            entry: The audit record to persist.
        """
        try:
            self._collection.insert_one(entry.model_dump(mode="json"))
        except PyMongoError:
            logger.warning(
                "Audit write failed for action %s on aggregate %s",
                entry.action,
                entry.aggregate_id,
            )
