import jwt
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.shared.auth import (
    AuthSettings,
    InvalidTokenError,
    JWTValidator,
    TokenClaims,
    build_auth_dependency,
)

_PRIVATE_KEY = """-----BEGIN RSA PRIVATE KEY-----
MIIEpQIBAAKCAQEAkqezWjRJCRRnQYjT/bZb/2jPbJAgkmibNaxwerJl3BGXuU9D
oLlrrba2ipB6PAeWuR6eD9QXPUIc+PGuL08JC8pCWbElsRvklakb1GppCdrkVJha
FRJLIAqyX5p9uB1dcYtZHvVsX1OumjjS1U2wqpub+vjnjIFy9Qd9urQg15S/+/li
C7EajkwnK18T0/E8HsPQne9VZKgKcn1XeIF4TYz5dr/qC90cUA2XPC6WPZ6HKEV4
NDN33o8zWVFA6NtJLFpUWHVrwK3Xu8EmM0yQKXGTdht5zhhAicqDlYOTf26kjvJE
jTVrURzTkyGUT2QjJIBFCSqYWMOgUe06JkmpOQIDAQABAoIBAAPiNAIuA0cdxrQ6
Et8TnrEPTfrigDJQWdfchqgBJGhlAN8T5ccSUfMqNQBLXilLzCZ/1JC3vZvOLeU7
xTCUh7lLtGEaq1Ra2D1MWqPP45MyvDwvQqdvMhUZo2qbtTuUb36LwaLrveByX1vP
KGokogqKj2FgiQU0Al7RwXcZwQrkZ8Ka+HuVfv6yVRS1urJe4PL0XTdVqD5mwUqV
zdS6BseBZYrLbCYQd+yanO4SSktAjUivnB39s40ZFP617R/O3rxI6Noxji+qPKuq
wVTMT1HMb76X+NV3suh4yhGpQ5yTi+3H1uc5MNbAelumshdal3mETN5gjs9pxrKp
ioGH1ecCgYEAyB3MF8ftaRSp2M6WNMuZt5TYDlcQcYqFE3WVHmKRkbXcQb5I2BIj
tQTb3Fmti9sy5C2g7tEozQ1l5SXbseQvGNSoGrp0q4VPtqrrXOwy4cGQdS5HRowh
4KsZ2IP0s0X1kp1ikSFE161cKLf/CKXwIARi4RQaKPYO2OuYymtGFScCgYEAu5v8
TfHAziMShMlg5FQAlqIQ59yvAx15YEIl5MfHaLCX2wU/irZxfryfUsptg/+c5iJD
pysptiGIlPYuaRL7UgZ4wCETzBLjWmMCCfO8zsSM4okRuMLhJtU4cXlaw+0wIGzD
vnm3xug5Kkim0wxnbPJF5fWXYJC3RSjIpdr5Cp8CgYEAiUKm8sjXNvRNa8CHlr7w
ONOHPo7JYJe6n5ZPKgBCCMfMw+tY25vVkhw7EfEQ8JTxW0FQ2X3tlnhSI9LL1kDF
bSqwA2VRETTncEvcFGiOnfq+syGDEgicVBYILFKWTUD3KBF7wkAnkCgAxo0uCSiI
g+1+RRQcvWvI01EGBBGAiJECgYEAm0mDz2h5tKZnH64oGxZE3moLIEAURLnSy5A1
GWcbcVYqe8meTMyyqLqsDbUsbQPY9MwLv4UEo5KiINqck7B4ge6FaFJ4toQz1474
ExDCiUs7ag8Wsh3si14VuCdAr8fV/CDK7RCGw4dYOd2k6C/uM8ldffiIcg+XAxG8
8zuKw/UCgYEAsk6Vo6APF8EL+O77BeqEv8sPE1G1zgvngSlcWzEX2lkbpjCxadGQ
ZJXHiMe7kvYhiQFTe9htI7v1P63iFEMQOyj552Xm82XB9+AaK5oyNqY+siJbf47V
PkEERzfXr/J70690Vn3i3hBwWZ6VZsEGFsd1oDGceQ0GYOOFk+c7NeA=
-----END RSA PRIVATE KEY-----"""

_PUBLIC_KEY = """-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAkqezWjRJCRRnQYjT/bZb
/2jPbJAgkmibNaxwerJl3BGXuU9DoLlrrba2ipB6PAeWuR6eD9QXPUIc+PGuL08J
C8pCWbElsRvklakb1GppCdrkVJhaFRJLIAqyX5p9uB1dcYtZHvVsX1OumjjS1U2w
qpub+vjnjIFy9Qd9urQg15S/+/liC7EajkwnK18T0/E8HsPQne9VZKgKcn1XeIF4
TYz5dr/qC90cUA2XPC6WPZ6HKEV4NDN33o8zWVFA6NtJLFpUWHVrwK3Xu8EmM0yQ
KXGTdht5zhhAicqDlYOTf26kjvJEjTVrURzTkyGUT2QjJIBFCSqYWMOgUe06Jkmp
OQIDAQAB
-----END PUBLIC KEY-----"""


def _make_token(payload: dict) -> str:  # type: ignore[type-arg]
    return jwt.encode(payload, _PRIVATE_KEY, algorithm="RS256")


@pytest.fixture()
def validator() -> JWTValidator:
    return JWTValidator(public_key=_PUBLIC_KEY, algorithm="RS256")


def test_auth_settings_fails_without_public_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("AUTH_JWT_PUBLIC_KEY", raising=False)

    with pytest.raises(ValidationError):
        AuthSettings()


def test_auth_settings_loads(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AUTH_JWT_PUBLIC_KEY", _PUBLIC_KEY)

    settings = AuthSettings()

    assert settings.auth_jwt_algorithm == "RS256"
    assert settings.auth_jwt_audience is None


def test_validator_returns_claims_for_valid_token(validator: JWTValidator) -> None:
    token = _make_token(
        {"sub": "user-123", "email": "user@example.com", "roles": ["admin"]}
    )

    claims = validator.validate(token)

    assert claims.sub == "user-123"
    assert claims.email == "user@example.com"
    assert claims.roles == ["admin"]


def test_validator_raises_for_invalid_signature(validator: JWTValidator) -> None:
    token = _make_token({"sub": "user-123"}) + "tampered"

    with pytest.raises(InvalidTokenError):
        validator.validate(token)


def test_validator_raises_for_malformed_token(validator: JWTValidator) -> None:
    with pytest.raises(InvalidTokenError):
        validator.validate("not.a.token")


def test_validator_defaults_missing_optional_claims(validator: JWTValidator) -> None:
    token = _make_token({"sub": "user-456"})

    claims = validator.validate(token)

    assert claims.email is None
    assert claims.roles == []


def test_token_claims_model() -> None:
    claims = TokenClaims(sub="user-123", email="user@example.com", roles=["viewer"])

    assert claims.sub == "user-123"


def test_auth_middleware_returns_401_without_header(validator: JWTValidator) -> None:
    app = FastAPI()
    get_current_user = build_auth_dependency(validator)

    @app.get("/protected")
    def protected(
        claims: TokenClaims = __import__("fastapi").Depends(get_current_user),
    ) -> dict:  # type: ignore[type-arg]
        return {"sub": claims.sub}

    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/protected")

    assert response.status_code == 401


def test_auth_middleware_returns_401_for_invalid_token(validator: JWTValidator) -> None:
    app = FastAPI()
    get_current_user = build_auth_dependency(validator)

    @app.get("/protected")
    def protected(
        claims: TokenClaims = __import__("fastapi").Depends(get_current_user),
    ) -> dict:  # type: ignore[type-arg]
        return {"sub": claims.sub}

    client = TestClient(app, raise_server_exceptions=False)
    response = client.get(
        "/protected", headers={"Authorization": "Bearer not.a.valid.token"}
    )

    assert response.status_code == 401


def test_auth_middleware_returns_claims_for_valid_token(
    validator: JWTValidator,
) -> None:
    app = FastAPI()
    get_current_user = build_auth_dependency(validator)

    @app.get("/protected")
    def protected(
        claims: TokenClaims = __import__("fastapi").Depends(get_current_user),
    ) -> dict:  # type: ignore[type-arg]
        return {"sub": claims.sub}

    token = _make_token({"sub": "user-789"})
    client = TestClient(app)
    response = client.get("/protected", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    assert response.json()["sub"] == "user-789"
