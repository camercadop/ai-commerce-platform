import logging

from fastapi import HTTPException, Request

from app.shared.auth.claims import TokenClaims
from app.shared.auth.validator import InvalidTokenError, JWTValidator

logger = logging.getLogger(__name__)


def build_auth_dependency(validator: JWTValidator):  # type: ignore[no-untyped-def]
    """Build a FastAPI dependency that validates the Bearer token on each request.

    Returns a callable suitable for use with FastAPI's Depends mechanism.
    Inject the returned dependency into route handlers that require authentication.

    The dependency extracts the Bearer token from the Authorization header,
    validates it using the provided JWTValidator, and returns the typed claims.
    Responds with 401 if the header is missing or the token is invalid.

    Args:
        validator: The JWTValidator instance configured at application startup.

    Returns:
        A FastAPI dependency callable that yields TokenClaims.
    """

    def get_current_user(request: Request) -> TokenClaims:
        """Extract and validate the Bearer token from the Authorization header.

        Raises:
            HTTPException 401: If the Authorization header is missing, malformed,
                or contains an invalid token.
        """
        authorization = request.headers.get("Authorization")
        if not authorization or not authorization.startswith("Bearer "):
            logger.warning("Missing or malformed Authorization header")
            raise HTTPException(status_code=401, detail="Authorization header required")

        token = authorization.removeprefix("Bearer ")

        try:
            return validator.validate(token)
        except InvalidTokenError:
            raise HTTPException(
                status_code=401, detail="Invalid or expired token"
            ) from None

    return get_current_user
