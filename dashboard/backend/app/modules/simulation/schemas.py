from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field


class SimulationRequest(BaseModel):
    scenario_type: str = Field(..., description="ROOM_UNAVAILABLE, TECH_UNAVAILABLE, PART_SHORTAGE, SWITCH_FAILURE, SIMULTANEOUS_DISRUPTION")
    target_node_id: Optional[UUID] = None
    target_node_code: Optional[str] = None
    affected_user_id: Optional[UUID] = None
    part_sku: Optional[str] = None
    time_window_start: Optional[datetime] = None
    time_window_end: Optional[datetime] = None
    description: Optional[str] = None


class PlanOption(BaseModel):
    plan_id: str  # "PLAN_A", "PLAN_B"
    name: str
    strategy: str
    actions: List[str]
    trade_offs: Dict[str, Any]
    sla_impact_minutes: int
    estimated_cost: float
    disruption_score: int  # 0 to 100
    recommended: bool


class ConsequenceStep(BaseModel):
    step_number: int
    title: str
    entity_type: str  # FAULT, ROOM_LOCK, EXAM_CLASH, CONTINGENCY_HOLD, PART_SHORTAGE, APPROVAL
    entity_id: str
    description: str
    severity: str  # CRITICAL, HIGH, MEDIUM, LOW


class SimulationResponse(BaseModel):
    simulation_id: UUID
    scenario_type: str
    target_node_code: Optional[str]
    target_node_name: Optional[str]
    headline: str
    consequence_chain: List[ConsequenceStep]
    plan_a: PlanOption
    plan_b: PlanOption
    recommended_plan: str
    state_fingerprint: str
    created_at: datetime
    is_executed: bool = False
    executed_at: Optional[datetime] = None


class ExecuteSimulationRequest(BaseModel):
    selected_plan: str = Field(default="PLAN_A")  # "PLAN_A" or "PLAN_B"

