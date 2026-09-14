import pytest
from pydantic import ValidationError

from app.catalog.schemas import (
    UpdateBrandRequest,
    UpdateCategoryAttributeRequest,
    UpdateCategoryRequest,
    UpdateProductRequest,
    UpdateVariantRequest,
)


class TestUpdateCategoryRequest:
    def test_raises_if_no_fields_provided(self) -> None:
        with pytest.raises(ValidationError):
            UpdateCategoryRequest()

    def test_accepts_name_only(self) -> None:
        req = UpdateCategoryRequest(name="Electronics")

        assert req.name == "Electronics"

    def test_accepts_description_only(self) -> None:
        req = UpdateCategoryRequest(description="A category")

        assert req.description == "A category"

    def test_accepts_parent_id_only(self) -> None:
        import uuid

        parent_id = uuid.uuid4()
        req = UpdateCategoryRequest(parent_id=parent_id)

        assert req.parent_id == parent_id


class TestUpdateBrandRequest:
    def test_raises_if_no_fields_provided(self) -> None:
        with pytest.raises(ValidationError):
            UpdateBrandRequest()

    def test_accepts_name_only(self) -> None:
        req = UpdateBrandRequest(name="Acme")

        assert req.name == "Acme"

    def test_accepts_website_only(self) -> None:
        req = UpdateBrandRequest(website="https://acme.com")

        assert req.website == "https://acme.com"

    def test_accepts_contact_email_only(self) -> None:
        req = UpdateBrandRequest(contact_email="contact@acme.com")

        assert req.contact_email == "contact@acme.com"

    def test_accepts_description_only(self) -> None:
        req = UpdateBrandRequest(description="A brand")

        assert req.description == "A brand"


class TestUpdateProductRequest:
    def test_raises_if_no_fields_provided(self) -> None:
        with pytest.raises(ValidationError):
            UpdateProductRequest()

    def test_accepts_name_only(self) -> None:
        req = UpdateProductRequest(name="Widget")

        assert req.name == "Widget"

    def test_accepts_sku_only(self) -> None:
        req = UpdateProductRequest(sku="SKU-001")

        assert req.sku == "SKU-001"

    def test_accepts_status_only(self) -> None:
        req = UpdateProductRequest(status="active")

        assert req.status == "active"

    def test_accepts_base_price_only(self) -> None:
        from decimal import Decimal

        req = UpdateProductRequest(base_price=Decimal("9.99"))

        assert req.base_price == Decimal("9.99")


class TestUpdateVariantRequest:
    def test_raises_if_no_fields_provided(self) -> None:
        with pytest.raises(ValidationError):
            UpdateVariantRequest()

    def test_accepts_sku_only(self) -> None:
        req = UpdateVariantRequest(sku="VAR-001")

        assert req.sku == "VAR-001"

    def test_accepts_price_only(self) -> None:
        from decimal import Decimal

        req = UpdateVariantRequest(price=Decimal("4.99"))

        assert req.price == Decimal("4.99")

    def test_accepts_attributes_only(self) -> None:
        req = UpdateVariantRequest(attributes={"color": "red"})

        assert req.attributes == {"color": "red"}


class TestUpdateCategoryAttributeRequest:
    def test_raises_if_no_fields_provided(self) -> None:
        with pytest.raises(ValidationError):
            UpdateCategoryAttributeRequest()

    def test_accepts_key_only(self) -> None:
        req = UpdateCategoryAttributeRequest(key="color")

        assert req.key == "color"

    def test_accepts_value_type_only(self) -> None:
        req = UpdateCategoryAttributeRequest(value_type="number")

        assert req.value_type == "number"

    def test_accepts_required_only(self) -> None:
        req = UpdateCategoryAttributeRequest(required=True)

        assert req.required is True
