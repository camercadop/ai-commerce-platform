import uuid

from pydantic import BaseModel


class InvalidActorId(ValueError):
    """Raised when the JWT subject claim cannot be parsed as a UUID.

    This indicates the identity provider is issuing non-UUID subject claims,
    which is incompatible with the platform's actor identity model.
    """


class TokenClaims(BaseModel):
    """Typed representation of the decoded JWT claims.

    Only the claims the platform depends on are declared here. Additional
    claims present in the token are ignored. Consumers must use these fields
    directly — never decode the token again downstream.
    """

    sub: str
    email: str | None = None
    roles: list[str] = []

    def actor_id(self) -> uuid.UUID:
        """Parse the subject claim as a UUID and return it as the actor identity.

        Raises:
            InvalidActorId: If the subject claim is not a valid UUID string.
        """
        try:
            return uuid.UUID(self.sub)
        except ValueError as exc:
            raise InvalidActorId(
                f"JWT subject claim is not a valid UUID: {self.sub!r}"
            ) from exc
