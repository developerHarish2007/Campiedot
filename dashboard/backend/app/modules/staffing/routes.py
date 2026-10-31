from typing import Optional, List
from uuid import UUID
from fastapi import APIRouter, Depends, status
from app.core.security import get_current_user, require_roles, CurrentUser
from app.database import acquire_db_connection
from app.modules.staffing.schemas import (
    AssignTechnicianRequest,
    AssignTechnicianResponse,
    ToggleAvailabilityRequest,
    ToggleAvailabilityResponse,
    TechnicianSummary,
    RegisterWorkerRequest,
    WorkerDetail,
)
from app.modules.staffing.service import StaffingService

router = APIRouter(prefix="", tags=["Staffing & Workforce"])


@router.get("/staff/technicians", response_model=List[TechnicianSummary])
async def list_technicians(
    current_user: CurrentUser = Depends(get_current_user),
):
    async with acquire_db_connection(
        actor_id=current_user.id,
        actor_role=current_user.role,
        dept_id=current_user.department_id,
    ) as conn:
        return await StaffingService.list_technicians(conn)


@router.post("/work-orders/{id}/assign", response_model=AssignTechnicianResponse)
async def assign_technician_to_work_order(
    id: UUID,
    request: Optional[AssignTechnicianRequest] = None,
    current_user: CurrentUser = Depends(require_roles(["DEPT_MANAGER", "FACILITIES_ADMIN", "SYS_ADMIN"])),
):
    tech_id = request.technician_id if request else None
    worker_name = request.worker_name if request else None
    worker_email = request.worker_email if request else None
    worker_role = request.worker_role if request else None

    async with acquire_db_connection(
        actor_id=current_user.id,
        actor_role=current_user.role,
        dept_id=current_user.department_id,
    ) as conn:
        async with conn.transaction():
            return await StaffingService.assign_technician(
                conn,
                work_order_id=id,
                technician_id=tech_id,
                worker_name=worker_name,
                worker_email=worker_email,
                worker_role=worker_role,
                actor_id=current_user.id
            )


@router.post("/staff/{id}/availability", response_model=ToggleAvailabilityResponse)
async def toggle_staff_availability(
    id: UUID,
    request: ToggleAvailabilityRequest,
    current_user: CurrentUser = Depends(get_current_user),
):
    # Technicians can toggle their own availability; managers/admins can toggle any staff
    if current_user.role not in ("FACILITIES_ADMIN", "SYS_ADMIN", "DEPT_MANAGER") and current_user.id != id:
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Technicians may only toggle their own availability.")

    async with acquire_db_connection(
        actor_id=current_user.id,
        actor_role=current_user.role,
        dept_id=current_user.department_id,
    ) as conn:
        async with conn.transaction():
            return await StaffingService.toggle_availability(
                conn,
                technician_id=id,
                is_available=request.is_available,
                reason=request.reason,
                actor_id=current_user.id
            )


@router.get("/staff/workers", response_model=List[WorkerDetail])
async def list_workers(
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    Returns registered technicians and maintenance personnel.
    """
    async with acquire_db_connection(
        actor_id=current_user.id,
        actor_role=current_user.role,
        dept_id=current_user.department_id,
    ) as conn:
        return await StaffingService.list_registered_workers(conn)


@router.post("/staff/workers", response_model=WorkerDetail, status_code=status.HTTP_201_CREATED)
async def register_worker(
    request: RegisterWorkerRequest,
    current_user: CurrentUser = Depends(require_roles(["SYS_ADMIN", "FACILITIES_ADMIN"])),
):
    """
    Registers a maintenance worker (e.g. Electrician, Plumber) manually.
    Admin only: SYS_ADMIN, FACILITIES_ADMIN.
    """
    async with acquire_db_connection(
        actor_id=current_user.id,
        actor_role=current_user.role,
        dept_id=current_user.department_id,
    ) as conn:
        async with conn.transaction():
            return await StaffingService.register_worker(
                conn,
                full_name=request.full_name,
                email=request.email,
                role=request.role
            )


@router.delete("/staff/workers/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_worker(
    id: UUID,
    current_user: CurrentUser = Depends(require_roles(["SYS_ADMIN", "FACILITIES_ADMIN"])),
):
    """
    Deregisters a maintenance worker. Admin only.
    """
    async with acquire_db_connection(
        actor_id=current_user.id,
        actor_role=current_user.role,
        dept_id=current_user.department_id,
    ) as conn:
        async with conn.transaction():
            await StaffingService.delete_worker(conn, id)


