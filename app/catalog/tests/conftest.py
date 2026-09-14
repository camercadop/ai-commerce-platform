import os

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.catalog.app import create_app
from app.catalog.routes import _auth_dependency, _db_dependency
from app.shared.auth import AuthSettings, TokenClaims
from app.shared.db import BaseModel, DatabaseSettings, build_session_factory

TEST_DATABASE_URL = os.environ["TEST_DATABASE_URL"]


@pytest.fixture(scope="session", autouse=True)
def setup_schema() -> None:
    """Create all tables in the test database once per session."""
    session_factory = build_session_factory(TEST_DATABASE_URL)
    engine = session_factory.kw["bind"]
    BaseModel.metadata.create_all(engine)


@pytest.fixture
def app() -> FastAPI:
    """Return a configured catalog app wired to the test database."""
    db_settings = DatabaseSettings(database_base_url=TEST_DATABASE_URL)
    auth_settings = AuthSettings(
        auth_jwt_public_key="test-key",
        auth_jwt_algorithm="HS256",
        auth_jwt_audience=None,
    )
    fastapi_app = create_app(db_settings, auth_settings)

    session_factory = build_session_factory(TEST_DATABASE_URL)
    claims = TokenClaims(sub="sub-test", email="test@example.com")

    def override_db():  # type: ignore[return]
        with session_factory() as session:
            yield session

    def override_auth() -> TokenClaims:
        return claims

    fastapi_app.dependency_overrides[_db_dependency] = override_db
    fastapi_app.dependency_overrides[_auth_dependency] = override_auth

    return fastapi_app


@pytest.fixture(autouse=True)
def clean_tables(app: FastAPI) -> None:
    """Truncate all catalog tables between tests to ensure isolation."""
    session_factory = build_session_factory(TEST_DATABASE_URL)
    with session_factory() as session:
        session.execute(
            __import__("sqlalchemy").text(
                "TRUNCATE catalog_category_attributes, catalog_variants, "
                "catalog_products, catalog_categories, catalog_brands "
                "RESTART IDENTITY CASCADE"
            )
        )
        session.commit()


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    """Return a TestClient for the catalog app."""
    return TestClient(app)
