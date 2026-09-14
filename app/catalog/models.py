import uuid
from typing import Any

from sqlalchemy import (
    UUID,
    Boolean,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.shared.db import BaseModel, SoftDeleteMixin, TimestampMixin


class Category(SoftDeleteMixin, TimestampMixin, BaseModel):
    """A product category organized in a hierarchical tree structure."""

    __tablename__ = "catalog_categories"

    __table_args__ = (
        Index("idx_catalog_categories_parent_id", "parent_id"),
        Index(
            "uq_catalog_categories_parent_id_name",
            func.lower(text("name")),
            "parent_id",
            unique=True,
            postgresql_where=text("parent_id IS NOT NULL"),
        ),
        Index(
            "uq_catalog_categories_root_name",
            func.lower(text("name")),
            unique=True,
            postgresql_where=text("parent_id IS NULL"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    # Unique identifier for this category.

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    # Human-readable name of the category.

    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Long-form description of the category for display or SEO.

    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "catalog_categories.id",
            name="fk_catalog_categories_parent_id",
        ),
        nullable=True,
    )
    # Identifier of the parent category for hierarchical grouping.

    products: Mapped[list[Product]] = relationship("Product", back_populates="category")
    # Products in this category.

    child_categories: Mapped[list[Category]] = relationship(
        "Category",
        backref="parent_category",
        remote_side=[id],
    )
    # Direct child categories of this category.

    attributes: Mapped[list[CategoryAttribute]] = relationship(
        "CategoryAttribute", back_populates="category", cascade="all, delete-orphan"
    )
    # Attribute definitions applicable to products in this category.


class Brand(SoftDeleteMixin, TimestampMixin, BaseModel):
    """A manufacturer or brand associated with products."""

    __tablename__ = "catalog_brands"

    __table_args__ = (
        UniqueConstraint(
            "name",
            name="uq_catalog_brands_name",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    # Unique identifier for this brand.

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    # Display name of the brand.

    website: Mapped[str | None] = mapped_column(String(500), nullable=True)
    # Official website URL for the brand.

    contact_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # Contact email for the brand representative.

    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Description of the brand.

    products: Mapped[list[Product]] = relationship("Product", back_populates="brand")
    # Products associated with this brand.


class Product(SoftDeleteMixin, TimestampMixin, BaseModel):
    """A sellable product in the catalog."""

    __tablename__ = "catalog_products"

    __table_args__ = (
        UniqueConstraint("sku", name="uq_catalog_products_sku"),
        Index("idx_catalog_products_category_id", "category_id"),
        Index("idx_catalog_products_brand_id", "brand_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    # Unique identifier for this product.

    sku: Mapped[str] = mapped_column(String(255), nullable=False)
    # Stock-keeping unit, unique business identifier for this product.

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    # Human-readable product name displayed in the catalog.

    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Product description or long-form marketing text.

    category_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "catalog_categories.id",
            name="fk_catalog_products_category_id",
        ),
        nullable=True,
    )
    # Identifier of the category this product belongs to.

    brand_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "catalog_brands.id",
            name="fk_catalog_products_brand_id",
        ),
        nullable=True,
    )
    # Identifier of the brand this product belongs to.

    base_price: Mapped[object] = mapped_column(Numeric(10, 2), nullable=False)
    # Listed price for this product in its base currency.

    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")
    # Lifecycle status of the product (draft, active, archived).

    specs: Mapped[dict[str, str] | None] = mapped_column(JSONB, nullable=True)
    # Free-form JSON map of descriptive product metadata (e.g. material, care
    # instructions, country of origin).

    category: Mapped[Category] = relationship("Category", back_populates="products")
    # The category this product belongs to.

    brand: Mapped[Brand] = relationship("Brand", back_populates="products")
    # The brand this product belongs to.

    variants: Mapped[list[Variant]] = relationship(
        "Variant", back_populates="product", cascade="all, delete-orphan"
    )
    # Sellable variants of this product.


class Variant(SoftDeleteMixin, TimestampMixin, BaseModel):
    """A sellable variant of a product (e.g. size or color option)."""

    __tablename__ = "catalog_variants"

    __table_args__ = (
        UniqueConstraint("sku", name="uq_catalog_variants_sku"),
        Index("idx_catalog_variants_product_id", "product_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    # Unique identifier for this variant.

    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "catalog_products.id",
            name="fk_catalog_variants_product_id",
        ),
        nullable=False,
    )
    # Identifier of the parent product this variant belongs to.

    sku: Mapped[str] = mapped_column(String(255), nullable=False)
    # Stock-keeping unit, unique identifier for this variant.

    price: Mapped[object] = mapped_column(Numeric(10, 2), nullable=False)
    # Listed price for this variant in the product's currency.

    attributes: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default="{}"
    )
    # Variant-specific attributes like color, size, material.

    product: Mapped[Product] = relationship("Product", back_populates="variants")
    # The parent product this variant belongs to.


class CategoryAttribute(SoftDeleteMixin, TimestampMixin, BaseModel):
    """An attribute definition applicable to products in a category."""

    __tablename__ = "catalog_category_attributes"

    __table_args__ = (
        UniqueConstraint(
            "category_id",
            "key",
            name="uq_catalog_category_attributes_category_id_key",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    # Unique identifier for this attribute definition.

    category_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "catalog_categories.id",
            name="fk_catalog_category_attributes_category_id",
        ),
        nullable=False,
    )
    # Identifier of the category this attribute definition applies to.

    key: Mapped[str] = mapped_column(String(100), nullable=False)
    # Attribute dimension name (e.g. color, size).

    value_type: Mapped[str] = mapped_column(String(20), nullable=False)
    # Expected value type for this attribute (string, number, boolean, object).

    required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # Whether variants in this category must supply this attribute.

    category: Mapped[Category] = relationship("Category", back_populates="attributes")
    # The category this attribute definition applies to.
