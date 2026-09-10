from app.shared.config import AppSettings


class MongoSettings(AppSettings):
    """Configuration for the MongoDB audit log connection.

    All values are required and validated at startup. A missing or invalid
    value causes the application to fail before serving any traffic (ADR-015).
    """

    mongo_username: str
    mongo_password: str
    mongo_host: str
    mongo_port: int
    mongo_database: str

    @property
    def uri(self) -> str:
        """Return the MongoDB connection URI."""
        return (
            f"mongodb://{self.mongo_username}:{self.mongo_password}"
            f"@{self.mongo_host}:{self.mongo_port}"
        )
