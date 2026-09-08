from pydantic import BaseModel


class TokenClaims(BaseModel):
    """Typed representation of the decoded JWT claims.

    Only the claims the platform depends on are declared here. Additional
    claims present in the token are ignored. Consumers must use these fields
    directly — never decode the token again downstream.
    """

    sub: str
    email: str | None = None
    roles: list[str] = []
