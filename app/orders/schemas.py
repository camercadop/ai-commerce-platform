import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class PlaceOrderRequest(BaseModel):
    """Request schema for placing an order from a cart."""

    cart_id: uuid.UUID


class OrderItemResponse(BaseModel):
    """Response schema for an order item."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    variant_id: uuid.UUID
    quantity: int
    unit_price: Decimal
    discount_value: Decimal
    discount_percent: Decimal
    tax_value: Decimal
    tax_percent: Decimal
    created_at: datetime
    updated_at: datetime


class OrderAdjustmentResponse(BaseModel):
    """Response schema for an order-level adjustment."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    kind: str
    percent: Decimal
    value: Decimal
    created_at: datetime
    updated_at: datetime


class OrderResponse(BaseModel):
    """Response schema for an order, including line items and adjustments."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    cart_id: uuid.UUID
    customer_id: uuid.UUID | None
    status: str
    subtotal: Decimal
    discount_total: Decimal
    tax_total: Decimal
    total_amount: Decimal
    items: list[OrderItemResponse]
    adjustments: list[OrderAdjustmentResponse]
    created_at: datetime
    updated_at: datetime
