import uuid
from datetime import datetime

from sqlalchemy import func, select

from app.catalog.models import Brand, Category, CategoryAttribute, Product, Variant
from app.shared.db import BaseRepository


class CategoryRepository(BaseRepository[Category]):
    """Repository for Category persistence operations.

    Provides lookup by name and listing by parent in addition to the base
    CRUD interface. All queries exclude soft-deleted records.
    """

    model_class = Category

    def get_by_name(
        self, name: str, parent_id: uuid.UUID | None = None
    ) -> Category | None:
        """Return the active category matching the given name and parent, or None.

        Args:
            name: The category name to look up.
            parent_id: The parent category UUID, or None for root categories.
        """
        stmt = (
            select(Category)
            .where(func.lower(Category.name) == name.lower())
            .where(
                Category.parent_id.is_(None)
                if parent_id is None
                else Category.parent_id == parent_id
            )
            .where(Category.deleted_at.is_(None))
        )
        return self.session.execute(stmt).scalar_one_or_none()

    def list_root(
        self,
        limit: int,
        cursor: tuple[datetime, uuid.UUID] | None = None,
    ) -> list[Category]:
        """Return a page of active root categories (those with no parent).

        Args:
            limit: Maximum number of records to return.
            cursor: Exclusive lower bound as (created_at, id) for keyset pagination.
        """
        return self.list_page(Category.parent_id.is_(None), limit=limit, cursor=cursor)

    def list_by_parent(
        self,
        parent_id: uuid.UUID,
        limit: int,
        cursor: tuple[datetime, uuid.UUID] | None = None,
    ) -> list[Category]:
        """Return a page of active categories under the given parent.

        Args:
            parent_id: The parent category UUID.
            limit: Maximum number of records to return.
            cursor: Exclusive lower bound as (created_at, id) for keyset pagination.
        """
        return self.list_page(
            Category.parent_id == parent_id, limit=limit, cursor=cursor
        )


class BrandRepository(BaseRepository[Brand]):
    """Repository for Brand persistence operations.

    Provides lookup by name in addition to the base CRUD interface.
    All queries exclude soft-deleted records.
    """

    model_class = Brand

    def get_by_name(self, name: str) -> Brand | None:
        """Return the active brand matching the given name, or None.

        Args:
            name: The brand name to look up.
        """
        return self.find_one_by(name=name)


class ProductRepository(BaseRepository[Product]):
    """Repository for Product persistence operations.

    Provides lookup by SKU and listing by category or brand in addition to
    the base CRUD interface. All queries exclude soft-deleted records.
    """

    model_class = Product

    def get_by_sku(self, sku: str) -> Product | None:
        """Return the active product matching the given SKU, or None.

        Args:
            sku: The stock-keeping unit to look up.
        """
        return self.find_one_by(sku=sku)

    def list_by_category(
        self,
        category_id: uuid.UUID,
        limit: int,
        cursor: tuple[datetime, uuid.UUID] | None = None,
    ) -> list[Product]:
        """Return a page of active products belonging to the given category.

        Args:
            category_id: The UUID of the category.
            limit: Maximum number of records to return.
            cursor: Exclusive lower bound as (created_at, id) for keyset pagination.
        """
        return self.list_page(
            Product.category_id == category_id, limit=limit, cursor=cursor
        )

    def list_by_brand(
        self,
        brand_id: uuid.UUID,
        limit: int,
        cursor: tuple[datetime, uuid.UUID] | None = None,
    ) -> list[Product]:
        """Return a page of active products belonging to the given brand.

        Args:
            brand_id: The UUID of the brand.
            limit: Maximum number of records to return.
            cursor: Exclusive lower bound as (created_at, id) for keyset pagination.
        """
        return self.list_page(Product.brand_id == brand_id, limit=limit, cursor=cursor)


class VariantRepository(BaseRepository[Variant]):
    """Repository for Variant persistence operations.

    Provides lookup by SKU and listing by product in addition to the base
    CRUD interface. All queries exclude soft-deleted records.
    """

    model_class = Variant

    def get_by_sku(self, sku: str) -> Variant | None:
        """Return the active variant matching the given SKU, or None.

        Args:
            sku: The stock-keeping unit to look up.
        """
        return self.find_one_by(sku=sku)

    def list_by_product(
        self,
        product_id: uuid.UUID,
        limit: int,
        cursor: tuple[datetime, uuid.UUID] | None = None,
    ) -> list[Variant]:
        """Return a page of active variants belonging to the given product.

        Args:
            product_id: The UUID of the parent product.
            limit: Maximum number of records to return.
            cursor: Exclusive lower bound as (created_at, id) for keyset pagination.
        """
        return self.list_page(
            Variant.product_id == product_id, limit=limit, cursor=cursor
        )


class CategoryAttributeRepository(BaseRepository[CategoryAttribute]):
    """Repository for CategoryAttribute persistence operations.

    Provides listing by category and lookup by category and key in addition
    to the base CRUD interface.
    """

    model_class = CategoryAttribute

    def list_by_category(
        self,
        category_id: uuid.UUID,
        limit: int,
        cursor: tuple[datetime, uuid.UUID] | None = None,
    ) -> list[CategoryAttribute]:
        """Return a page of attribute definitions for the given category.

        Args:
            category_id: The UUID of the category.
            limit: Maximum number of records to return.
            cursor: Exclusive lower bound as (created_at, id) for keyset pagination.
        """
        return self.list_page(
            CategoryAttribute.category_id == category_id, limit=limit, cursor=cursor
        )

    def get_by_category_and_key(
        self, category_id: uuid.UUID, key: str
    ) -> CategoryAttribute | None:
        """Return the attribute definition matching the given category and key, or None.

        Args:
            category_id: The UUID of the category.
            key: The attribute dimension name (e.g. color, size).
        """
        return self.find_one_by(category_id=category_id, key=key)
