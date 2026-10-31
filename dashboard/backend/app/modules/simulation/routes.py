from uuid import UUID
from typing import Dict, Any
from fastapi import APIRouter, Depends, status
from app.core.security import get_current_user, CurrentUser, require_roles
from app.database import acquire_db_connection
from app.modules.simulation.schemas import (
    SimulationRequest,
    SimulationResponse,
    ExecuteSimulationRequest,
)
from app.modules.simulation.service import SimulationService

router = APIRouter(prefix="", tags=["What-If Simulator & Consequence Engine"])


@router.post("/simulations", response_model=SimulationResponse, status_code=status.HTTP_201_CREATED)
async def run_simulation(
    request: SimulationRequest,
    current_user: CurrentUser = Depends(require_roles(["SYS_ADMIN", "FACILITIES_ADMIN", "DEPT_MANAGER"])),
):
    """
    Executes a read-only What-If Dry-Run Consequence Simulation.
    Enforces the zero-mutation invariant: NEVER alters database state.
    """
    async with acquire_db_connection(
        actor_id=current_user.id,
        actor_role=current_user.role,
        dept_id=current_user.department_id,
    ) as conn:
        return await SimulationService.run_simulation(conn, request=request, actor_id=current_user.id)


@router.get("/simulations/{id}", response_model=SimulationResponse)
async def get_simulation(
    id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
):
    return await SimulationService.get_simulation(simulation_id=id)


@router.post("/simulations/{id}/execute")
async def execute_simulation(
    id: UUID,
    request: ExecuteSimulationRequest = None,
    current_user: CurrentUser = Depends(require_roles(["SYS_ADMIN", "FACILITIES_ADMIN"])),
):
    """
    Revalidates live operational state against dry-run dependencies.
    If valid, atomically applies the recovery plan in a single transaction.
    """
    selected_plan = request.selected_plan if request else "PLAN_A"
    async with acquire_db_connection(
        actor_id=current_user.id,
        actor_role=current_user.role,
        dept_id=current_user.department_id,
    ) as conn:
        async with conn.transaction():
            return await SimulationService.execute_simulation(
                conn,
                simulation_id=id,
                selected_plan=selected_plan,
                actor_id=current_user.id,
                actor_role=current_user.role,
            )

