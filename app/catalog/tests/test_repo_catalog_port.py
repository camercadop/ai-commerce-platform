import uuid
from datetime import UTC, datetime
from decimal import Decimal

from app.catalog.adapters import RepoCatalogPort
from app.catalog.tests.fakes import FakeVariantRepository, make_variant


def _port(variants=None) -> RepoCatalogPort:
    return RepoCatalogPort(repo=FakeVariantRepository(variants))


# ---------------------------------------------------------------------------
# RepoCatalogPort
# ---------------------------------------------------------------------------


class TestRepoCatalogPortGetVariantPrice:
    def test_returns_price_for_existing_variant(self) -> None:
        variant = make_variant(price=Decimal("19.99"))
        port = _port([variant])

        assert port.get_variant_price(variant.id) == Decimal("19.99")

    def test_returns_none_for_unknown_variant(self) -> None:
        port = _port()

        assert port.get_variant_price(uuid.uuid4()) is None

    def test_returns_none_for_soft_deleted_variant(self) -> None:
        variant = make_variant(deleted_at=datetime.now(UTC))
        port = _port([variant])

        assert port.get_variant_price(variant.id) is None
