from pydantic import field_validator

from app.shared.config import AppSettings


class AuthSettings(AppSettings):
    """Configuration for JWT validation.

    All values are validated at startup. A missing or invalid value causes
    the application to fail before serving any traffic (ADR-015).

    For RS256, set AUTH_JWT_SECRET to the PEM-encoded RSA public key.
    For HS256, set AUTH_JWT_SECRET to the shared secret string.
    The algorithm is controlled by AUTH_JWT_ALGORITHM.
    """

    auth_jwt_secret: str
    auth_jwt_algorithm: str = "RS256"
    auth_jwt_audience: str | None = None

    @field_validator("auth_jwt_audience", mode="before")
    @classmethod
    def _empty_str_to_none(cls, v: object) -> object:
        return None if v == "" else v
