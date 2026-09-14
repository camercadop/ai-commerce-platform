import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.shared.api import sanitize_strings

# ---------------------------------------------------------------------------
# Category
# ---------------------------------------------------------------------------


class CreateCategoryRequest(BaseModel):
    """Request schema for creating a new category."""

    name: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=5000)
    parent_id: uuid.UUID | None = None

    _strip = sanitize_strings("name", "description")


class UpdateCategoryRequest(BaseModel):
    """Request schema for partially updating a category.

    At least one field must be provided.
    """

    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=5000)
    parent_id: uuid.UUID | None = None

    _strip = sanitize_strings("name", "description")

    @model_validator(mode="after")
    def require_at_least_one_field(self) -> UpdateCategoryRequest:
        """Ensure at least one field is provided."""
        if self.name is None and self.description is None and self.parent_id is None:
            raise ValueError("At least one field must be provided.")
        return self


class CategoryResponse(BaseModel):
    """Response schema for a category."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: str | None
    parent_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# Brand
# ---------------------------------------------------------------------------


class CreateBrandRequest(BaseModel):
    """Request schema for creating a new brand."""

    name: str = Field(min_length=1, max_length=255)
    website: str | None = Field(default=None, max_length=500)
    contact_email: str | None = Field(
        default=None, max_length=255, pattern=r"^[^@]+@[^@]+\.[^@]+$"
    )
    description: str | None = Field(default=None, max_length=5000)

    _strip = sanitize_strings("name", "website", "contact_email", "description")


class UpdateBrandRequest(BaseModel):
    """Request schema for partially updating a brand.

    At least one field must be provided.
    """

    name: str | None = Field(default=None, min_length=1, max_length=255)
    website: str | None = Field(default=None, max_length=500)
    contact_email: str | None = Field(
        default=None, max_length=255, pattern=r"^[^@]+@[^@]+\.[^@]+$"
    )
    description: str | None = Field(default=None, max_length=5000)

    _strip = sanitize_strings("name", "website", "contact_email", "description")

    @model_validator(mode="after")
    def require_at_least_one_field(self) -> UpdateBrandRequest:
        """Ensure at least one field is provided."""
        if all(
            f is None
            for f in (self.name, self.website, self.contact_email, self.description)
        ):
            raise ValueError("At least one field must be provided.")
        return self


class BrandResponse(BaseModel):
    """Response schema for a brand."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    website: str | None
    contact_email: str | None
    description: str | None
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# Product
# ---------------------------------------------------------------------------


class CreateProductRequest(BaseModel):
    """Request schema for creating a new product."""

    sku: str = Field(min_length=1, max_length=255)
    name: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=5000)
    category_id: uuid.UUID | None = None
    brand_id: uuid.UUID | None = None
    base_price: Decimal = Field(gt=0, decimal_places=2)
    status: str = Field(default="draft", pattern="^(draft|active|archived)$")
    specs: dict[str, str] | None = None

    _strip = sanitize_strings("sku", "name", "description")


class UpdateProductRequest(BaseModel):
    """Request schema for partially updating a product.

    At least one field must be provided.
    """

    sku: str | None = Field(default=None, min_length=1, max_length=255)
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=5000)
    category_id: uuid.UUID | None = None
    brand_id: uuid.UUID | None = None
    base_price: Decimal | None = Field(default=None, gt=0, decimal_places=2)
    status: str | None = Field(default=None, pattern="^(draft|active|archived)$")
    specs: dict[str, str] | None = None

    _strip = sanitize_strings("sku", "name", "description")

    @model_validator(mode="after")
    def require_at_least_one_field(self) -> UpdateProductRequest:
        """Ensure at least one field is provided."""
        if all(
            f is None
            for f in (
                self.sku,
                self.name,
                self.description,
                self.category_id,
                self.brand_id,
                self.base_price,
                self.status,
                self.specs,
            )
        ):
            raise ValueError("At least one field must be provided.")
        return self


class ProductResponse(BaseModel):
    """Response schema for a product."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    sku: str
    name: str
    description: str | None
    category_id: uuid.UUID | None
    brand_id: uuid.UUID | None
    base_price: Decimal
    status: str
    specs: dict[str, str] | None
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# Variant
# ---------------------------------------------------------------------------


class CreateVariantRequest(BaseModel):
    """Request schema for creating a new product variant."""

    sku: str = Field(min_length=1, max_length=255)
    price: Decimal = Field(gt=0, decimal_places=2)
    attributes: dict[str, Any] = Field(default_factory=dict)

    _strip = sanitize_strings("sku")


class UpdateVariantRequest(BaseModel):
    """Request schema for partially updating a variant.

    At least one field must be provided.
    """

    sku: str | None = Field(default=None, min_length=1, max_length=255)
    price: Decimal | None = Field(default=None, gt=0, decimal_places=2)
    attributes: dict[str, Any] | None = None

    _strip = sanitize_strings("sku")

    @model_validator(mode="after")
    def require_at_least_one_field(self) -> UpdateVariantRequest:
        """Ensure at least one field is provided."""
        if self.sku is None and self.price is None and self.attributes is None:
            raise ValueError("At least one field must be provided.")
        return self


class VariantResponse(BaseModel):
    """Response schema for a product variant."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    product_id: uuid.UUID
    sku: str
    price: Decimal
    attributes: dict[str, Any]
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# CategoryAttribute
# ---------------------------------------------------------------------------


class CreateCategoryAttributeRequest(BaseModel):
    """Request schema for creating a category attribute definition."""

    key: str = Field(min_length=1, max_length=100)
    value_type: str = Field(pattern="^(string|number|boolean|object)$")
    required: bool = False

    _strip = sanitize_strings("key")


class UpdateCategoryAttributeRequest(BaseModel):
    """Request schema for partially updating a category attribute definition.

    At least one field must be provided.
    """

    key: str | None = Field(default=None, min_length=1, max_length=100)
    value_type: str | None = Field(
        default=None, pattern="^(string|number|boolean|object)$"
    )
    required: bool | None = None

    _strip = sanitize_strings("key")

    @model_validator(mode="after")
    def require_at_least_one_field(self) -> UpdateCategoryAttributeRequest:
        """Ensure at least one field is provided."""
        if self.key is None and self.value_type is None and self.required is None:
            raise ValueError("At least one field must be provided.")
        return self


class CategoryAttributeResponse(BaseModel):
    """Response schema for a category attribute definition."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    category_id: uuid.UUID
    key: str
    value_type: str
    required: bool
    created_at: datetime
    updated_at: datetime
