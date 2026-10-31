from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, Field

class CreateWorkOrderRequest(BaseModel):
    conversation_thread_id: Optional[str] = None
    target_node_id: Optional[UUID] = None
    category: Optional[str] = None
    reporter_urgency: str = Field(default="P2_MEDIUM")
    raw_description: str
    ai_summary: Optional[str] = None
    initial_state: str = Field(default="INGESTED")

class TransitionWorkOrderRequest(BaseModel):
    target_state: str
    reason: str
    resolution_notes: Optional[str] = None
    details: Optional[Dict[str, Any]] = None

class WorkOrderPartItem(BaseModel):
    part_id: UUID
    sku: str
    name: str
    requested_qty: int
    locked_unit_cost: Decimal
    status: str

class WorkOrderOut(BaseModel):
    id: UUID
    ticket_number: int
    conversation_thread_id: str
    reporter_user_id: UUID
    target_node_id: Optional[UUID] = None
    node_code: Optional[str] = None
    node_name: Optional[str] = None
    parent_master_wo_id: Optional[UUID] = None
    category: Optional[str] = None
    reporter_urgency: str
    calculated_priority: str
    impact_score: int
    state: str
    raw_description: str
    ai_summary: Optional[str] = None
    assigned_tech_id: Optional[UUID] = None
    assigned_tech_name: Optional[str] = None
    assigned_tech_email: Optional[str] = None
    assigned_tech_role: Optional[str] = None
    department_id: Optional[UUID] = None
    estimated_cost: Decimal
    estimated_duration_mins: int
    reassignment_count: int
    correlator_reporter_count: int
    sla_is_paused: bool
    sla_breached: bool
    blocked_reason: Optional[str] = None
    clarification_question: Optional[str] = None
    partial_slots: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime
    resolved_at: Optional[datetime] = None
    reserved_parts: List[WorkOrderPartItem] = []
    comments_count: int = 0
    worker_comments_count: int = 0
    admin_comments_count: int = 0
    latest_comment_author_role: Optional[str] = None
    latest_comment_message: Optional[str] = None
    latest_comment_at: Optional[datetime] = None

class WorkOrderTransitionResponse(BaseModel):
    work_order_id: UUID
    ticket_number: int
    previous_state: str
    new_state: str
    transitioned_by: UUID
    actor_role: str
    reason: str
    timestamp: datetime

class CreateWorkOrderCommentRequest(BaseModel):
    message: str = Field(..., min_length=1, description="Comment text from admin or technician")

class WorkOrderCommentOut(BaseModel):
    id: UUID
    work_order_id: UUID
    author_user_id: UUID
    author_name: str
    author_role: str
    message: str
    created_at: datetime
