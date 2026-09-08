from app.shared.config import AppSettings


class AuthSettings(AppSettings):
    """Configuration for JWT validation.

    All values are validated at startup. A missing or invalid value causes
    the application to fail before serving any traffic (ADR-015).

    The public key is provider-agnostic — it can be sourced from Keycloak,
    Auth0, or any OIDC-compliant provider. The identity domain is responsible
    for fetching and rotating it.
    """

    auth_jwt_public_key: str
    auth_jwt_algorithm: str = "RS256"
    auth_jwt_audience: str | None = None
