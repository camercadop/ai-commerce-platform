from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    """Base settings class for all domain configuration.

    Every domain must subclass this and declare its configuration keys as fields
    with types and validators. Missing or invalid values cause startup to fail
    with an explicit error — never silently defaulted (ADR-015).

    Subclasses must not read environment variables outside of this class.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )
