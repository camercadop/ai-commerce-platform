import uuid
from datetime import datetime

from pydantic import BaseModel, Field, model_validator

from app.shared.api import sanitize_strings


class RegisterCustomerRequest(BaseModel):
    """Request schema for registering a new customer profile."""

    identity_provider_id: str = Field(min_length=1, max_length=255)
    email: str = Field(min_length=1, max_length=255)
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)

    _strip = sanitize_strings(
        "identity_provider_id", "email", "first_name", "last_name"
    )


class UpdateProfileRequest(BaseModel):
    """Request schema for partially updating a customer profile.

    At least one field must be provided.
    """

    first_name: str | None = Field(default=None, min_length=1, max_length=100)
    last_name: str | None = Field(default=None, min_length=1, max_length=100)

    _strip = sanitize_strings("first_name", "last_name")

    @model_validator(mode="after")
    def require_at_least_one_field(self) -> UpdateProfileRequest:
        """Ensure at least one field is provided."""
        if self.first_name is None and self.last_name is None:
            raise ValueError("At least one field must be provided.")
        return self


class CustomerResponse(BaseModel):
    """Response schema for a customer profile."""

    id: uuid.UUID
    identity_provider_id: str
    email: str
    first_name: str
    last_name: str
    created_at: datetime


class AddAddressRequest(BaseModel):
    """Request schema for adding a new address to a customer profile."""

    label: str = Field(min_length=1, max_length=100)
    street: str = Field(min_length=1, max_length=255)
    city: str = Field(min_length=1, max_length=100)
    state: str = Field(min_length=1, max_length=100)
    country: str = Field(min_length=1, max_length=100)
    postal_code: str = Field(min_length=1, max_length=20)
    is_default: bool = False

    _strip = sanitize_strings(
        "label", "street", "city", "state", "country", "postal_code"
    )


class UpdateAddressRequest(BaseModel):
    """Request schema for partially updating an address.

    At least one field must be provided.
    """

    label: str | None = Field(default=None, min_length=1, max_length=100)
    street: str | None = Field(default=None, min_length=1, max_length=255)
    city: str | None = Field(default=None, min_length=1, max_length=100)
    state: str | None = Field(default=None, min_length=1, max_length=100)
    country: str | None = Field(default=None, min_length=1, max_length=100)
    postal_code: str | None = Field(default=None, min_length=1, max_length=20)
    is_default: bool | None = None

    _strip = sanitize_strings(
        "label", "street", "city", "state", "country", "postal_code"
    )

    @model_validator(mode="after")
    def require_at_least_one_field(self) -> UpdateAddressRequest:
        """Ensure at least one field is provided."""
        if all(
            f is None
            for f in (
                self.label,
                self.street,
                self.city,
                self.state,
                self.country,
                self.postal_code,
                self.is_default,
            )
        ):
            raise ValueError("At least one field must be provided.")
        return self


class AddressResponse(BaseModel):
    """Response schema for a customer address."""

    id: uuid.UUID
    customer_id: uuid.UUID
    label: str
    street: str
    city: str
    state: str
    country: str
    postal_code: str
    is_default: bool
    created_at: datetime


class UpsertPreferencesRequest(BaseModel):
    """Request schema for upserting customer preferences.

    Each key-value pair is inserted if the key does not exist, or updated
    if it does. Keys not present in the request are left unchanged.
    """

    preferences: dict[str, str] = Field(min_length=1, max_length=50)
