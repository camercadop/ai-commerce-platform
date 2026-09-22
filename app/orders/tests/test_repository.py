import os
import uuid
from typing import Generator

import pytest
from sqlalchemy.orm import Session

from app.orders.repository import OrderItemRepository, OrderRepository
from app.orders.tests.fakes import make_order, make_order_item
from app.shared.db import BaseModel, build_session_factory

TEST_DATABASE_URL = os.environ["TEST_DATABASE_URL"]
_session_factory = build_session_factory(TEST_DATABASE_URL)


@pytest.fixture(scope="module", autouse=True)
def setup_schema() -> None:
    session_factory = build_session_factory(TEST_DATABASE_URL)
    engine = session_factory.kw["bind"]
    BaseModel.metadata.create_all(engine)


@pytest.fixture
def session() -> Generator[Session, None, None]:
    with _session_factory() as s:
        yield s
        s.rollback()


# ---------------------------------------------------------------------------
# OrderRepository.get_with_items
# ---------------------------------------------------------------------------


class TestOrderRepositoryGetWithItems:
    def test_returns_order_with_items(self, session: Session) -> None:
        order = make_order()
        session.add(order)
        session.flush()
        item = make_order_item(order_id=order.id)
        session.add(item)
        session.flush()
        session.expire(order)

        repo = OrderRepository(session)

        result = repo.get_with_items(order.id)

        assert result is not None
        assert result.id == order.id
        assert len(result.items) == 1
        assert result.items[0].id == item.id

    def test_returns_none_when_not_found(self, session: Session) -> None:
        repo = OrderRepository(session)

        result = repo.get_with_items(uuid.uuid4())

        assert result is None


# ---------------------------------------------------------------------------
# OrderRepository.list_by_customer
# ---------------------------------------------------------------------------


class TestOrderRepositoryListByCustomer:
    def test_returns_orders_for_customer(self, session: Session) -> None:
        customer_id = uuid.uuid4()
        order_a = make_order(customer_id=customer_id)
        order_b = make_order(customer_id=customer_id)
        session.add(order_a)
        session.add(order_b)
        session.flush()

        repo = OrderRepository(session)

        result = repo.list_by_customer(customer_id)

        assert {o.id for o in result} == {order_a.id, order_b.id}

    def test_excludes_orders_from_other_customers(self, session: Session) -> None:
        customer_a = uuid.uuid4()
        customer_b = uuid.uuid4()
        order_a = make_order(customer_id=customer_a)
        order_b = make_order(customer_id=customer_b)
        session.add(order_a)
        session.add(order_b)
        session.flush()

        repo = OrderRepository(session)

        result = repo.list_by_customer(customer_a)

        assert len(result) == 1
        assert result[0].id == order_a.id

    def test_returns_empty_list_when_no_orders(self, session: Session) -> None:
        repo = OrderRepository(session)

        result = repo.list_by_customer(uuid.uuid4())

        assert result == []


# ---------------------------------------------------------------------------
# OrderItemRepository.list_by_order
# ---------------------------------------------------------------------------


class TestOrderItemRepositoryListByOrder:
    def test_returns_items_for_order(self, session: Session) -> None:
        order = make_order()
        session.add(order)
        session.flush()
        item_a = make_order_item(order_id=order.id)
        item_b = make_order_item(order_id=order.id)
        session.add(item_a)
        session.add(item_b)
        session.flush()

        repo = OrderItemRepository(session)

        result = repo.list_by_order(order.id)

        assert {i.id for i in result} == {item_a.id, item_b.id}

    def test_excludes_items_from_other_orders(self, session: Session) -> None:
        order_a = make_order()
        order_b = make_order()
        session.add(order_a)
        session.add(order_b)
        session.flush()
        item_a = make_order_item(order_id=order_a.id)
        item_b = make_order_item(order_id=order_b.id)
        session.add(item_a)
        session.add(item_b)
        session.flush()

        repo = OrderItemRepository(session)

        result = repo.list_by_order(order_a.id)

        assert len(result) == 1
        assert result[0].id == item_a.id

    def test_returns_empty_list_when_no_items(self, session: Session) -> None:
        repo = OrderItemRepository(session)

        result = repo.list_by_order(uuid.uuid4())

        assert result == []
