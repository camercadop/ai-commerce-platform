import os
import uuid
from unittest.mock import patch
from typing import Generator

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.cart.repository import CartItemRepository, CartRepository
from app.cart.tests.fakes import make_cart, make_cart_item
from app.shared.db import BaseModel, build_session_factory

TEST_DATABASE_URL = os.environ["TEST_DATABASE_URL"]


@pytest.fixture(scope="module", autouse=True)
def setup_schema() -> None:
    session_factory = build_session_factory(TEST_DATABASE_URL)
    engine = session_factory.kw["bind"]
    BaseModel.metadata.create_all(engine)


@pytest.fixture
def session() -> Generator[Session]:
    session_factory = build_session_factory(TEST_DATABASE_URL)
    with session_factory() as s:
        yield s
        s.rollback()


class TestCartRepositoryGetOrCreateBySessionId:
    def test_creates_cart_when_none_exists(self, session: Session) -> None:
        repo = CartRepository(session)

        cart, created = repo.get_or_create_by_session_id("s1")

        assert cart.session_id == "s1"
        assert cart.id is not None
        assert created is True

    def test_returns_existing_cart_when_found(self, session: Session) -> None:
        existing = make_cart(session_id="s1")
        session.add(existing)
        session.flush()

        repo = CartRepository(session)

        cart, created = repo.get_or_create_by_session_id("s1")

        assert cart.id == existing.id
        assert created is False

    def test_rolls_back_and_returns_existing_cart_on_integrity_error(
        self, session: Session
    ) -> None:
        existing = make_cart(session_id="s1")
        session.add(existing)
        session.commit()

        repo = CartRepository(session)

        with patch.object(
            CartRepository,
            "get_by_session_id",
            side_effect=[None, existing],
        ), patch.object(
            CartRepository,
            "create",
            side_effect=IntegrityError(None, None, Exception("unique constraint")),
        ), patch.object(session, "rollback") as mock_rollback:
            cart, created = repo.get_or_create_by_session_id("s1")

        assert cart.id == existing.id
        assert created is True
        mock_rollback.assert_called_once()


# ---------------------------------------------------------------------------
# CartRepository.get_by_session_id
# ---------------------------------------------------------------------------


class TestCartRepositoryGetBySessionId:
    def test_returns_cart_when_found(self, session: Session) -> None:
        cart = make_cart()
        session.add(cart)
        session.flush()

        repo = CartRepository(session)

        result = repo.get_by_session_id(cart.session_id)

        assert result is not None
        assert result.id == cart.id

    def test_returns_none_when_not_found(self, session: Session) -> None:
        repo = CartRepository(session)

        result = repo.get_by_session_id(str(uuid.uuid4()))

        assert result is None

    def test_excludes_soft_deleted(self, session: Session) -> None:
        from datetime import UTC, datetime

        cart = make_cart(deleted_at=datetime.now(UTC))
        session.add(cart)
        session.flush()

        repo = CartRepository(session)

        result = repo.get_by_session_id(cart.session_id)

        assert result is None


# ---------------------------------------------------------------------------
# CartRepository.get_by_customer_id
# ---------------------------------------------------------------------------


class TestCartRepositoryGetByCustomerId:
    def test_returns_cart_when_found(self, session: Session) -> None:
        customer_id = uuid.uuid4()
        cart = make_cart(customer_id=customer_id)
        session.add(cart)
        session.flush()

        repo = CartRepository(session)

        result = repo.get_by_customer_id(customer_id)

        assert result is not None
        assert result.id == cart.id

    def test_returns_none_when_not_found(self, session: Session) -> None:
        repo = CartRepository(session)

        result = repo.get_by_customer_id(uuid.uuid4())

        assert result is None

    def test_excludes_soft_deleted(self, session: Session) -> None:
        from datetime import UTC, datetime

        customer_id = uuid.uuid4()
        cart = make_cart(customer_id=customer_id, deleted_at=datetime.now(UTC))
        session.add(cart)
        session.flush()

        repo = CartRepository(session)

        result = repo.get_by_customer_id(customer_id)

        assert result is None


# ---------------------------------------------------------------------------
# CartRepository.get_with_items
# ---------------------------------------------------------------------------


class TestCartRepositoryGetWithItems:
    def test_returns_cart_with_items(self, session: Session) -> None:
        cart = make_cart()
        session.add(cart)
        session.flush()
        item = make_cart_item(cart_id=cart.id)
        session.add(item)
        session.flush()

        repo = CartRepository(session)

        result = repo.get_with_items(cart.id)

        assert result is not None
        assert result.id == cart.id
        assert len(result.items) == 1
        assert result.items[0].id == item.id

    def test_returns_none_when_not_found(self, session: Session) -> None:
        repo = CartRepository(session)

        result = repo.get_with_items(uuid.uuid4())

        assert result is None

    def test_excludes_soft_deleted(self, session: Session) -> None:
        from datetime import UTC, datetime

        cart = make_cart(deleted_at=datetime.now(UTC))
        session.add(cart)
        session.flush()

        repo = CartRepository(session)

        result = repo.get_with_items(cart.id)

        assert result is None


# ---------------------------------------------------------------------------
# CartItemRepository.get_by_cart_and_variant
# ---------------------------------------------------------------------------


class TestCartItemRepositoryGetByCartAndVariant:
    def test_returns_item_when_found(self, session: Session) -> None:
        cart = make_cart()
        session.add(cart)
        session.flush()
        item = make_cart_item(cart_id=cart.id)
        session.add(item)
        session.flush()

        repo = CartItemRepository(session)

        result = repo.get_by_cart_and_variant(cart.id, item.variant_id)

        assert result is not None
        assert result.id == item.id

    def test_returns_none_when_not_found(self, session: Session) -> None:
        repo = CartItemRepository(session)

        result = repo.get_by_cart_and_variant(uuid.uuid4(), uuid.uuid4())

        assert result is None


# ---------------------------------------------------------------------------
# CartItemRepository.list_by_cart
# ---------------------------------------------------------------------------


class TestCartItemRepositoryListByCart:
    def test_returns_items_for_cart(self, session: Session) -> None:
        cart = make_cart()
        session.add(cart)
        session.flush()
        item_a = make_cart_item(cart_id=cart.id)
        item_b = make_cart_item(cart_id=cart.id)
        session.add(item_a)
        session.add(item_b)
        session.flush()

        repo = CartItemRepository(session)

        result = repo.list_by_cart(cart.id)

        assert {i.id for i in result} == {item_a.id, item_b.id}

    def test_excludes_items_from_other_carts(self, session: Session) -> None:
        cart_a = make_cart()
        cart_b = make_cart()
        session.add(cart_a)
        session.add(cart_b)
        session.flush()
        item_a = make_cart_item(cart_id=cart_a.id)
        item_b = make_cart_item(cart_id=cart_b.id)
        session.add(item_a)
        session.add(item_b)
        session.flush()

        repo = CartItemRepository(session)

        result = repo.list_by_cart(cart_a.id)

        assert len(result) == 1
        assert result[0].id == item_a.id

    def test_returns_empty_list_when_no_items(self, session: Session) -> None:
        repo = CartItemRepository(session)

        result = repo.list_by_cart(uuid.uuid4())

        assert result == []
