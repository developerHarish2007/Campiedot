from typing import List, Optional
from uuid import UUID
from decimal import Decimal
from pydantic import BaseModel, Field


class InventoryPartOut(BaseModel):
    id: UUID
    sku: str
    name: str
    category: str
    physical_on_hand_qty: int
    available_qty: int
    reserved_qty: int
    reorder_threshold: int
    unit_cost: Decimal
    lead_time_hours: int


class PartReservationItem(BaseModel):
    part_id: UUID
    requested_qty: int = Field(gt=0)


class ReservePartsRequest(BaseModel):
    work_order_id: UUID
    items: List[PartReservationItem]


class PartReservationResult(BaseModel):
    part_id: UUID
    sku: str
    requested_qty: int
    status: str
    unit_cost: Decimal


class ReservePartsResponse(BaseModel):
    work_order_id: UUID
    all_reserved: bool
    work_order_state: str
    reservations: List[PartReservationResult]


class ReceiveStockItem(BaseModel):
    part_id: UUID
    quantity: int = Field(gt=0)
    unit_cost: Optional[Decimal] = None


class ReceiveStockRequest(BaseModel):
    items: List[ReceiveStockItem]
    supplier_reference: Optional[str] = None
    notes: Optional[str] = None


class CreatePartRequest(BaseModel):
    sku: str = Field(..., description="Unique Part SKU e.g. PART-AC-CAP-50")
    name: str = Field(..., description="Part Name e.g. 50 MFD Dual Motor Run Capacitor")
    category: str = Field(..., description="Category: ELECTRICAL, HVAC, PLUMBING, NETWORK, AV_EQUIPMENT, FURNITURE, STRUCTURAL_SAFETY")
    quantity: int = Field(default=0, ge=0, description="Initial physical quantity")
    unit_cost: Decimal = Field(default=Decimal("0.00"), ge=0, description="Unit cost in INR")
    reorder_threshold: int = Field(default=2, ge=0)
    lead_time_hours: int = Field(default=24, ge=1)


