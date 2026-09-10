import logging

import jwt
import jwt.exceptions

from app.shared.auth.claims import TokenClaims

logger = logging.getLogger(__name__)


class InvalidTokenError(Exception):
    """Raised when a JWT cannot be validated.

    Callers must treat this as an authentication failure and respond with 401.
    Never expose the underlying reason to the client — log it server-side only.
    """

    code = "INVALID_TOKEN"


class JWTValidator:
    """Validates JWTs against a configured public key and algorithm.

    Provider-agnostic — works with any OIDC-compliant token issuer.
    The concrete issuer (Keycloak, Auth0, etc.) is an identity domain concern.

    Args:
        public_key: PEM-encoded RSA public key used to verify token signatures.
        algorithm: JWT signing algorithm. Defaults to RS256.
        audience: Expected audience claim. Pass None to skip audience validation.
    """

    def __init__(
        self,
        public_key: str,
        algorithm: str = "RS256",
        audience: str | None = None,
    ) -> None:
        self._public_key = public_key
        self._algorithm = algorithm
        self._audience = audience

    def validate(self, token: str) -> TokenClaims:
        """Decode and validate a JWT, returning its typed claims.

        Args:
            token: The raw Bearer token string (without the "Bearer " prefix).

        Returns:
            TokenClaims populated from the verified token payload.

        Raises:
            InvalidTokenError: If the token is expired, has an invalid signature,
                is malformed, or fails audience validation.
        """
        try:
            options: jwt.types.Options = {"verify_aud": self._audience is not None}
            payload = jwt.decode(
                token,
                self._public_key,
                algorithms=[self._algorithm],
                audience=self._audience,
                options=options,
            )
            return TokenClaims.model_validate(payload)
        except jwt.exceptions.ExpiredSignatureError:
            logger.warning("JWT validation failed: token expired")
            raise InvalidTokenError("Token has expired") from None
        except jwt.exceptions.PyJWTError as exc:
            logger.warning("JWT validation failed: %s", exc)
            raise InvalidTokenError("Token is invalid") from exc
