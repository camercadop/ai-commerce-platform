import os
import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy.orm import Session

from app.identity.models import Address, Customer, CustomerPreference
from app.identity.repository import AddressRepository, CustomerRepository
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


def _make_customer(session: Session) -> Customer:
    customer = Customer(
        id=uuid.uuid4(),
        identity_provider_id=str(uuid.uuid4()),
        email=f"{uuid.uuid4()}@example.com",
        first_name="Jane",
        last_name="Doe",
    )
    session.add(customer)
    session.flush()
    return customer


def _make_address(
    session: Session,
    customer_id: uuid.UUID,
    *,
    label: str = "Home",
    is_default: bool = False,
    deleted_at: datetime | None = None,
) -> Address:
    address = Address(
        id=uuid.uuid4(),
        customer_id=customer_id,
        label=label,
        street="123 Main St",
        city="Springfield",
        state="IL",
        country="US",
        postal_code="62701",
        is_default=is_default,
    )
    address.deleted_at = deleted_at
    session.add(address)
    session.flush()
    return address


# ---------------------------------------------------------------------------
# CustomerRepository
# ---------------------------------------------------------------------------


class TestCustomerRepositoryUpsertPreference:
    def test_is_noop_when_customer_does_not_exist(self, session: Session) -> None:
        """upsert_preference must silently return when the customer is not found,
        even if a preference with the same key exists for another customer."""
        customer = _make_customer(session)
        pref = CustomerPreference(
            id=uuid.uuid4(),
            customer_id=customer.id,
            key="language",
            value="en",
        )
        session.add(pref)
        session.flush()

        repo = CustomerRepository(session)
        repo.upsert_preference(uuid.uuid4(), "language", "es")

        session.refresh(pref)
        assert pref.value == "en"


# ---------------------------------------------------------------------------
# AddressRepository
# ---------------------------------------------------------------------------


class TestAddressRepositoryClearDefault:
    def test_unsets_default_on_active_addresses(self, session: Session) -> None:
        """clear_default must set is_default=False on all active addresses."""
        customer = _make_customer(session)
        a1 = _make_address(session, customer.id, label="Home", is_default=True)
        a2 = _make_address(session, customer.id, label="Work", is_default=True)

        AddressRepository(session).clear_default(customer.id)
        session.expire_all()

        assert session.get(Address, a1.id).is_default is False
        assert session.get(Address, a2.id).is_default is False

    def test_does_not_unset_default_on_soft_deleted_addresses(
        self, session: Session
    ) -> None:
        """clear_default must leave soft-deleted addresses untouched."""
        customer = _make_customer(session)
        deleted = _make_address(
            session,
            customer.id,
            label="Old",
            is_default=True,
            deleted_at=datetime.now(UTC),
        )

        AddressRepository(session).clear_default(customer.id)
        session.expire_all()

        assert session.get(Address, deleted.id).is_default is True
