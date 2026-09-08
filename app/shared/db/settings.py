from app.shared.config import AppSettings


class DatabaseSettings(AppSettings):
    """Configuration for the SQLAlchemy database connection.

    All values are required and validated at startup. A missing or invalid
    value causes the application to fail before serving any traffic (ADR-015).
    """

    database_url: str
