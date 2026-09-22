import os
import uuid

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.cart.app import create_app
from app.cart.routes import (
    _audit_dependency,
    _auth_dependency,
    _broker_dependency,
    _db_dependency,
)
from app.shared.audit_log import NoOpAuditRepository
from app.shared.auth import AuthSettings, TokenClaims
from app.shared.db import BaseModel, DatabaseSettings, build_session_factory
from app.shared.events import NoOpMessageBroker

TEST_DATABASE_URL = os.environ["TEST_DATABASE_URL"]

ACTOR_ID = uuid.uuid4()


@pytest.fixture(scope="session", autouse=True)
def setup_schema() -> None:
    """Create all tables in the test database once per session."""
    session_factory = build_session_factory(TEST_DATABASE_URL)
    engine = session_factory.kw["bind"]
    BaseModel.metadata.create_all(engine)


@pytest.fixture
def app() -> FastAPI:
    """Return a configured cart app wired to the test database."""
    db_settings = DatabaseSettings(database_base_url=TEST_DATABASE_URL)
    auth_settings = AuthSettings(
        auth_jwt_public_key="test-key",
        auth_jwt_algorithm="HS256",
        auth_jwt_audience=None,
    )
    fastapi_app = create_app(db_settings, auth_settings)

    session_factory = build_session_factory(TEST_DATABASE_URL)
    claims = TokenClaims(sub=str(ACTOR_ID), email="test@example.com")

    def override_db():
        with session_factory() as session:
            yield session

    def override_auth() -> TokenClaims:
        return claims

    fastapi_app.dependency_overrides[_db_dependency] = override_db
    fastapi_app.dependency_overrides[_auth_dependency] = override_auth
    fastapi_app.dependency_overrides[_audit_dependency] = NoOpAuditRepository
    fastapi_app.dependency_overrides[_broker_dependency] = lambda: NoOpMessageBroker()

    return fastapi_app


@pytest.fixture(autouse=True)
def clean_tables(app: FastAPI) -> None:
    """Truncate all cart tables between tests to ensure isolation."""
    session_factory = build_session_factory(TEST_DATABASE_URL)
    with session_factory() as session:
        session.execute(
            __import__("sqlalchemy").text(
                "TRUNCATE commerce_cart_items, commerce_cart_carts "
                "RESTART IDENTITY CASCADE"
            )
        )
        session.commit()


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    """Return a TestClient for the cart app."""
    return TestClient(app)
