import uuid
from decimal import Decimal

from app.cart.ports import CatalogPort
from app.catalog.repository import VariantRepository


class RepoCatalogPort(CatalogPort):
    """CatalogPort implementation that reads variant prices from the catalog repository.

    Soft-deleted variants are treated as not found and return None.
    """

    def __init__(self, repo: VariantRepository) -> None:
        """Args:
        repo: VariantRepository bound to the current request session.
        """
        self._repo = repo

    def get_variant_price(self, variant_id: uuid.UUID) -> Decimal | None:
        """Return the current price for the given variant, or None if not found.

        Args:
            variant_id: The UUID of the product variant.

        Returns:
            The variant price, or None if the variant does not exist or is
            soft-deleted.
        """
        variant = self._repo.get_by_id(variant_id)
        return variant.price if variant is not None else None
