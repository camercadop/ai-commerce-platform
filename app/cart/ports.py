import uuid
from abc import ABC, abstractmethod
from decimal import Decimal


class CatalogPort(ABC):
    """Abstract port for reading catalog data.

    Provides price lookups for cart operations. The concrete implementation
    lives outside app/cart/ (e.g. app/catalog/). Domain code must never
    depend on a concrete implementation directly (ADR-004).
    """

    @abstractmethod
    def get_variant_price(self, variant_id: uuid.UUID) -> Decimal | None:
        """Return the current price for the given variant, or None if not found.

        Args:
            variant_id: The UUID of the product variant.

        Returns:
            The current price or None if the variant does not exist.
        """


class InventoryPort(ABC):
    """Abstract port for checking product variant inventory.

    The concrete implementation lives outside app/cart/ (e.g. app/inventory/).
    Domain code must never depend on a concrete implementation directly
    (ADR-004).
    """

    @abstractmethod
    def check_availability(self, variant_id: uuid.UUID, quantity: int) -> bool:
        """Return True if the variant has sufficient stock for the requested quantity.

        Args:
            variant_id: The UUID of the product variant.
            quantity: The quantity to check availability for.

        Returns:
            True if sufficient stock is available, False otherwise.
        """
