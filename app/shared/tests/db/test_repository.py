import os
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.orm import Session

from app.identity.models import Customer
from app.identity.repository import CustomerRepository
from app.shared.db import BaseModel, build_session_factory

TEST_DATABASE_URL = os.environ["TEST_DATABASE_URL"]


@pytest.fixture(scope="module", autouse=True)
def setup_schema() -> None:
    """Create all tables in the test database once per module."""
    session_factory = build_session_factory(TEST_DATABASE_URL)
    engine = session_factory.kw["bind"]
    BaseModel.metadata.create_all(engine)


@pytest.fixture
def session() -> Session:
    """Provide a session that rolls back after each test."""
    session_factory = build_session_factory(TEST_DATABASE_URL)
    with session_factory() as s:
        yield s
        s.rollback()


def _make_customer(session: Session, created_at: datetime) -> Customer:
    customer = Customer(
        id=uuid.uuid4(),
        identity_provider_id=str(uuid.uuid4()),
        email=f"{uuid.uuid4()}@example.com",
        first_name="Jane",
        last_name="Doe",
    )
    customer.created_at = created_at
    customer.updated_at = created_at
    session.add(customer)
    session.flush()
    return customer


class TestListPage:
    def test_cursor_excludes_records_at_or_before_cursor(
        self, session: Session
    ) -> None:
        base = datetime(2024, 1, 1, tzinfo=UTC)
        c1 = _make_customer(session, base)
        c2 = _make_customer(session, base + timedelta(seconds=1))
        c3 = _make_customer(session, base + timedelta(seconds=2))

        repo = CustomerRepository(session)
        result = repo.list_page(limit=10, cursor=(c1.created_at, c1.id))

        ids = [r.id for r in result]
        assert c1.id not in ids
        assert c2.id in ids
        assert c3.id in ids
