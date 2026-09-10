import pytest
from pydantic import ValidationError

from app.identity.schemas import (
    AddAddressRequest,
    RegisterCustomerRequest,
    UpdateAddressRequest,
    UpdateProfileRequest,
    UpsertPreferencesRequest,
)


class TestRegisterCustomerRequest:
    def test_valid(self) -> None:
        req = RegisterCustomerRequest(
            identity_provider_id="sub-123",
            email="jane@example.com",
            first_name="Jane",
            last_name="Doe",
        )
        assert req.identity_provider_id == "sub-123"

    def test_strips_newlines(self) -> None:
        req = RegisterCustomerRequest(
            identity_provider_id="sub\n123",
            email="jane@example.com",
            first_name="Jane\r",
            last_name="Doe",
        )
        assert req.identity_provider_id == "sub123"
        assert req.first_name == "Jane"

    def test_rejects_empty_fields(self) -> None:
        with pytest.raises(ValidationError):
            RegisterCustomerRequest(
                identity_provider_id="",
                email="jane@example.com",
                first_name="Jane",
                last_name="Doe",
            )


class TestUpdateProfileRequest:
    def test_valid_with_one_field(self) -> None:
        req = UpdateProfileRequest(first_name="Alice")
        assert req.first_name == "Alice"

    def test_raises_if_no_fields(self) -> None:
        with pytest.raises(ValidationError):
            UpdateProfileRequest()

    def test_strips_newlines(self) -> None:
        req = UpdateProfileRequest(first_name="Ali\nce")
        assert req.first_name == "Alice"


class TestAddAddressRequest:
    def test_valid(self) -> None:
        req = AddAddressRequest(
            label="Home",
            street="123 Main St",
            city="Springfield",
            state="IL",
            country="US",
            postal_code="62701",
        )
        assert req.is_default is False

    def test_strips_newlines(self) -> None:
        req = AddAddressRequest(
            label="Ho\nme",
            street="123 Main St",
            city="Springfield",
            state="IL",
            country="US",
            postal_code="62701",
        )
        assert req.label == "Home"


class TestUpdateAddressRequest:
    def test_valid_with_one_field(self) -> None:
        req = UpdateAddressRequest(city="Shelbyville")
        assert req.city == "Shelbyville"

    def test_raises_if_no_fields(self) -> None:
        with pytest.raises(ValidationError):
            UpdateAddressRequest()


class TestUpsertPreferencesRequest:
    def test_valid(self) -> None:
        req = UpsertPreferencesRequest(preferences={"language": "en"})
        assert req.preferences == {"language": "en"}

    def test_raises_if_empty(self) -> None:
        with pytest.raises(ValidationError):
            UpsertPreferencesRequest(preferences={})
