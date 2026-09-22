import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, computed_field

from app.shared.api import sanitize_strings


class CreateCartRequest(BaseModel):
    """Request schema for creating a new cart."""

    session_id: str = Field(min_length=1, max_length=255)
    customer_id: uuid.UUID | None = None

    _strip = sanitize_strings("session_id")


class ClaimCartRequest(BaseModel):
    """Request schema for claiming an anonymous cart."""

    customer_id: uuid.UUID


class AddCartItemRequest(BaseModel):
    """Request schema for adding an item to a cart."""

    variant_id: uuid.UUID
    quantity: int = Field(gt=0)


class UpdateCartItemRequest(BaseModel):
    """Request schema for updating a cart item quantity."""

    quantity: int = Field(gt=0)


class CartItemResponse(BaseModel):
    """Response schema for a cart item."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    variant_id: uuid.UUID
    quantity: int
    unit_price: Decimal
    status: str
    created_at: datetime
    updated_at: datetime


class CartResponse(BaseModel):
    """Response schema for a cart, including items and computed subtotal."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    session_id: str
    customer_id: uuid.UUID | None
    status: str
    items: list[CartItemResponse]
    created_at: datetime
    updated_at: datetime

    @computed_field
    def subtotal(self) -> Decimal:
        """Sum of item totals, computed at serialization time."""
        return sum(
            (item.quantity * item.unit_price for item in self.items), Decimal("0")
        )
