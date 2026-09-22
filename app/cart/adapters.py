import uuid
from decimal import Decimal

from app.cart.ports import CatalogPort, InventoryPort


class StubCatalogPort(CatalogPort):
    """No-op catalog port that always returns None for prices.

    Use in tests and local development where a real catalog service is
    not available. Never use in production.
    """

    def get_variant_price(self, variant_id: uuid.UUID) -> Decimal | None:
        return None


class StubInventoryPort(InventoryPort):
    """No-op inventory port that always reports items as available.

    Use in tests and local development where a real inventory service is
    not available. Never use in production.
    """

    def check_availability(self, variant_id: uuid.UUID, quantity: int) -> bool:
        return True
