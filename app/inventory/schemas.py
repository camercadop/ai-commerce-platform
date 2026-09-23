import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CreateInventoryItemRequest(BaseModel):
    variant_id: uuid.UUID
    initial_quantity: int = Field(..., ge=0)


class AdjustStockRequest(BaseModel):
    delta: int = Field(..., description="Non-zero delta to adjust stock")
    note: str | None = Field(None, max_length=255)


class ReserveStockRequest(BaseModel):
    variant_id: uuid.UUID
    order_id: uuid.UUID
    quantity: int = Field(..., gt=0)


class InventoryItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    variant_id: uuid.UUID
    quantity_on_hand: int
    quantity_reserved: int
    quantity_available: int
    created_at: datetime
    updated_at: datetime


class ReservationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    inventory_item_id: uuid.UUID
    order_id: uuid.UUID
    quantity: int
    status: str
    created_at: datetime
    updated_at: datetime
