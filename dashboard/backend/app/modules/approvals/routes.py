from uuid import UUID
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from app.core.security import get_current_user, CurrentUser, require_roles
from app.database import acquire_db_connection
from app.modules.approvals.schemas import (
    ApprovalResponse,
    ApprovalDecisionRequest,
)
from app.modules.approvals.service import ApprovalsService

router = APIRouter(prefix="", tags=["Approvals & Delegation of Authority"])


@router.get("/approvals", response_model=List[ApprovalResponse])
async def list_approvals(
    status: Optional[str] = Query(None),
    current_user: CurrentUser = Depends(get_current_user),
):
    async with acquire_db_connection(
        actor_id=current_user.id,
        actor_role=current_user.role,
        dept_id=current_user.department_id,
    ) as conn:
        return await ApprovalsService.list_approvals(conn, status=status)


@router.post("/approvals/{id}/approve", response_model=ApprovalResponse)
async def approve_request(
    id: UUID,
    request: ApprovalDecisionRequest = None,
    current_user: CurrentUser = Depends(require_roles(["DEPT_MANAGER", "FACILITIES_ADMIN", "PROCUREMENT_APPROVER", "SYS_ADMIN"])),
):
    notes = request.notes if request else None
    async with acquire_db_connection(
        actor_id=current_user.id,
        actor_role=current_user.role,
        dept_id=current_user.department_id,
    ) as conn:
        async with conn.transaction():
            return await ApprovalsService.process_decision(
                conn,
                approval_id=id,
                decision="APPROVED",
                actor_id=current_user.id,
                actor_role=current_user.role,
                notes=notes
            )


@router.post("/approvals/{id}/reject", response_model=ApprovalResponse)
async def reject_request(
    id: UUID,
    request: ApprovalDecisionRequest = None,
    current_user: CurrentUser = Depends(require_roles(["DEPT_MANAGER", "FACILITIES_ADMIN", "PROCUREMENT_APPROVER", "SYS_ADMIN"])),
):
    notes = request.notes if request else None
    async with acquire_db_connection(
        actor_id=current_user.id,
        actor_role=current_user.role,
        dept_id=current_user.department_id,
    ) as conn:
        async with conn.transaction():
            return await ApprovalsService.process_decision(
                conn,
                approval_id=id,
                decision="REJECTED",
                actor_id=current_user.id,
                actor_role=current_user.role,
                notes=notes
            )

