from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel, Field


class TechnicianScoreBreakdown(BaseModel):
    technician_id: UUID
    full_name: str
    email: str
    skill_proficiency: int
    active_workload: int
    max_workload: int
    base_building: Optional[str] = None
    proximity_bonus: float
    total_score: float
    explanation: str


class AssignTechnicianRequest(BaseModel):
    technician_id: Optional[UUID] = None  # None for auto-assignment or if creating new worker
    worker_name: Optional[str] = None     # Full name of worker, e.g. "Rajesh Kumar"
    worker_email: Optional[str] = None    # Email of worker, e.g. "rajesh.kumar@easwari.edu"
    worker_role: Optional[str] = None     # ELECTRICAL, PLUMBING, HVAC, NETWORK, AV_EQUIPMENT, STRUCTURAL_SAFETY


class AssignTechnicianResponse(BaseModel):
    work_order_id: UUID
    assigned_tech_id: UUID
    assigned_tech_name: str
    assigned_tech_email: str
    assigned_tech_role: Optional[str] = None
    score: float
    explanation: str
    work_order_state: str
    email_dispatched: bool = False
    email_dispatch_id: Optional[str] = None
    email_subject: Optional[str] = None


class TechnicianSummary(BaseModel):
    id: UUID
    full_name: str
    email: str
    roles: List[str] = []
    is_available: bool = True
    active_workload_count: int = 0


class ToggleAvailabilityRequest(BaseModel):
    is_available: bool
    reason: Optional[str] = None


class DynamicReassignmentItem(BaseModel):
    work_order_id: UUID
    ticket_number: int
    previous_tech_id: UUID
    new_tech_id: Optional[UUID]
    new_tech_name: Optional[str]
    reassignment_count: int
    escalated_to_admin: bool
    reason: str


class ToggleAvailabilityResponse(BaseModel):
    technician_id: UUID
    is_available: bool
    affected_work_orders_count: int
    reassignments: List[DynamicReassignmentItem]


class RegisterWorkerRequest(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=120)
    email: str = Field(..., min_length=5, max_length=120)
    role: str = Field(default="ELECTRICAL")  # ELECTRICAL, PLUMBING, HVAC, NETWORK, AV_EQUIPMENT, STRUCTURAL_SAFETY


class WorkerDetail(BaseModel):
    id: UUID
    full_name: str
    email: str
    role: str
    skills: List[str] = []
    is_available: bool = True
    active_workload_count: int = 0
    max_concurrent_workload: int = 5


