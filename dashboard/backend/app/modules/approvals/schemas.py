from typing import Optional
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field


class ApprovalResponse(BaseModel):
    id: UUID
    work_order_id: UUID
    ticket_number: Optional[int] = None
    work_order_description: Optional[str] = None
    approval_type: str
    requested_by_user_id: UUID
    requested_by_name: Optional[str] = None
    approved_by_user_id: Optional[UUID] = None
    approved_by_name: Optional[str] = None
    requested_amount: float
    snapshot_hash: str
    status: str
    invalidation_reason: Optional[str] = None
    created_at: datetime
    decided_at: Optional[datetime] = None


class ApprovalDecisionRequest(BaseModel):
    notes: Optional[str] = Field(default=None)

