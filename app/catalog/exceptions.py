from app.shared.exceptions import ResourceAlreadyExists, ResourceNotFound


class CatalogError(Exception):
    """Base exception for the catalog domain.

    Catch this to handle any catalog domain failure as a group.
    Prefer catching specific subclasses when the failure mode matters.
    """

    code = "CATALOG_ERROR"


class CategoryNotFound(ResourceNotFound):
    """Raised when a category does not exist or has been soft-deleted."""

    code = "CATEGORY_NOT_FOUND"
    resource_name = "Category"


class CategoryAlreadyExists(ResourceAlreadyExists):
    """Raised when creating a category whose name already exists under the same
    parent."""

    code = "CATEGORY_ALREADY_EXISTS"
    resource_name = "Category"


class BrandNotFound(ResourceNotFound):
    """Raised when a brand does not exist or has been soft-deleted."""

    code = "BRAND_NOT_FOUND"
    resource_name = "Brand"


class BrandAlreadyExists(ResourceAlreadyExists):
    """Raised when creating a brand whose name is already taken."""

    code = "BRAND_ALREADY_EXISTS"
    resource_name = "Brand"


class ProductNotFound(ResourceNotFound):
    """Raised when a product does not exist or has been soft-deleted."""

    code = "PRODUCT_NOT_FOUND"
    resource_name = "Product"


class ProductAlreadyExists(ResourceAlreadyExists):
    """Raised when creating a product whose SKU is already taken."""

    code = "PRODUCT_ALREADY_EXISTS"
    resource_name = "Product"


class VariantNotFound(ResourceNotFound):
    """Raised when a variant does not exist or has been soft-deleted."""

    code = "VARIANT_NOT_FOUND"
    resource_name = "Variant"


class VariantAlreadyExists(ResourceAlreadyExists):
    """Raised when creating a variant whose SKU is already taken."""

    code = "VARIANT_ALREADY_EXISTS"
    resource_name = "Variant"


class CategoryAttributeNotFound(ResourceNotFound):
    """Raised when a category attribute does not exist."""

    code = "CATEGORY_ATTRIBUTE_NOT_FOUND"
    resource_name = "CategoryAttribute"


class CategoryAttributeAlreadyExists(ResourceAlreadyExists):
    """Raised when creating a category attribute whose key already exists for the
    category."""

    code = "CATEGORY_ATTRIBUTE_ALREADY_EXISTS"
    resource_name = "CategoryAttribute"


class InvalidVariantAttributes(CatalogError):
    """Raised when variant attributes fail validation against the category's attribute
    schema.

    The violations attribute maps each failing key to a human-readable reason.
    """

    code = "INVALID_VARIANT_ATTRIBUTES"

    def __init__(self, violations: dict[str, str]) -> None:
        """Initialize with a map of attribute key to violation reason.

        Args:
            violations: Dict mapping attribute key to the reason it failed validation.
        """
        self.violations = violations
        details = "; ".join(f"{k}: {v}" for k, v in violations.items())
        super().__init__(f"Invalid variant attributes: {details}")
