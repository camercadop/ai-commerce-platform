# auth

Provides provider-agnostic JWT validation, typed token claims, and a FastAPI dependency
factory for protecting routes. Works with any OIDC-compliant token issuer — no
provider-specific SDK is referenced here.

## Package layout

```
auth/
├── __init__.py     # Package entry point
├── claims.py       # Token identity layer
├── middleware.py   # FastAPI auth dependency factory
├── settings.py     # JWT configuration
└── validator.py    # JWT validation layer
```

## Public API

| Symbol | Description |
| --- | --- |
| `JWTValidator` | Validates a Bearer token against a PEM public key and returns `TokenClaims` |
| `InvalidTokenError` | Raised by `JWTValidator.validate()` on any validation failure |
| `TokenClaims` | Typed model of the decoded JWT payload (`sub`, `email`, `roles`) |
| `InvalidActorId` | Raised by `TokenClaims.actor_id()` when `sub` is not a valid UUID |
| `build_auth_dependency(validator)` | Returns a FastAPI dependency that extracts and validates the Bearer token |
| `AuthSettings` | `AppSettings` subclass for JWT public key, algorithm, and audience |

### TokenClaims

| Field | Type | Description |
| --- | --- | --- |
| `sub` | `str` | Subject claim — the actor's identity string |
| `email` | `str \| None` | Email claim, if present in the token |
| `roles` | `list[str]` | Roles claim; defaults to `[]` if absent |

Call `claims.actor_id()` to parse `sub` as a `UUID`. Raises `InvalidActorId` if the
subject is not a valid UUID string.

## Middleware

`build_auth_dependency(validator)` returns a FastAPI dependency that runs on every
request injected with it. It:

1. Extracts the `Authorization` header and asserts it starts with `Bearer `.
2. Passes the token to `JWTValidator.validate()`.
3. Returns the resulting `TokenClaims` to the route handler on success.
4. Raises `HTTP 401` if the header is absent, malformed, or the token is invalid.

The dependency never propagates `InvalidTokenError` to the caller — it is always
converted to a `401` response. Security enforcement decisions are logged server-side
as warnings.

```python
from typing import Annotated
from fastapi import Depends
from app.shared.auth import JWTValidator, TokenClaims, build_auth_dependency

validator = JWTValidator(public_key=settings.auth_jwt_public_key)
get_current_user = build_auth_dependency(validator)
CurrentUser = Annotated[TokenClaims, Depends(get_current_user)]


@router.get("/orders")
def list_orders(claims: CurrentUser) -> list[OrderResponse]:
    actor_id = claims.actor_id()
    ...
```

## Configuration

| Key | Description | Default |
| --- | --- | --- |
| `AUTH_JWT_PUBLIC_KEY` | PEM-encoded RSA public key for signature verification | required |
| `AUTH_JWT_ALGORITHM` | JWT signing algorithm | `RS256` |
| `AUTH_JWT_AUDIENCE` | Expected audience claim; `None` skips audience validation | `None` |

## Error handling

| Exception | HTTP status | Trigger |
| --- | --- | --- |
| `InvalidTokenError` | `401` | Missing header, malformed token, expired signature, invalid audience |
| `InvalidActorId` | caller's responsibility | `sub` claim is not a valid UUID |

Never expose the underlying validation reason to the client — log it server-side only.
