from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Query, status
from app.core.security import get_current_user, require_roles, CurrentUser
from app.database import acquire_db_connection
from app.modules.inventory.schemas import (
    InventoryPartOut,
    ReservePartsRequest,
    ReservePartsResponse,
    ReceiveStockRequest,
    CreatePartRequest,
)
from app.modules.inventory.service import InventoryService

router = APIRouter(prefix="/inventory", tags=["Inventory & Procurement"])


@router.get("", response_model=List[InventoryPartOut])
async def get_inventory(
    category: Optional[str] = Query(None, description="Filter by issue category"),
    only_shortages: bool = Query(False, description="Filter only parts at or below reorder threshold"),
    current_user: CurrentUser = Depends(get_current_user),
):
    async with acquire_db_connection(
        actor_id=current_user.id,
        actor_role=current_user.role,
        dept_id=current_user.department_id,
    ) as conn:
        return await InventoryService.list_parts(conn, category=category, only_shortages=only_shortages)


@router.post("/reservations", response_model=ReservePartsResponse)
async def reserve_parts(
    request: ReservePartsRequest,
    current_user: CurrentUser = Depends(require_roles(["TECHNICIAN", "FACILITIES_ADMIN", "SYS_ADMIN"])),
):
    async with acquire_db_connection(
        actor_id=current_user.id,
        actor_role=current_user.role,
        dept_id=current_user.department_id,
    ) as conn:
        async with conn.transaction():
            return await InventoryService.reserve_parts(conn, request, actor_id=current_user.id)


@router.post("/receipts", response_model=List[InventoryPartOut], status_code=status.HTTP_201_CREATED)
async def receive_stock(
    request: ReceiveStockRequest,
    current_user: CurrentUser = Depends(require_roles(["PROCUREMENT_APPROVER", "FACILITIES_ADMIN", "SYS_ADMIN"])),
):
    async with acquire_db_connection(
        actor_id=current_user.id,
        actor_role=current_user.role,
        dept_id=current_user.department_id,
    ) as conn:
        async with conn.transaction():
            return await InventoryService.receive_stock(conn, request, actor_id=current_user.id)


@router.post("/parts", response_model=InventoryPartOut, status_code=status.HTTP_201_CREATED)
async def create_part(
    request: CreatePartRequest,
    current_user: CurrentUser = Depends(require_roles(["SYS_ADMIN", "FACILITIES_ADMIN"])),
):
    """
    Registers a new part/material in the campus inventory.
    """
    async with acquire_db_connection(
        actor_id=current_user.id,
        actor_role=current_user.role,
        dept_id=current_user.department_id,
    ) as conn:
        async with conn.transaction():
            return await InventoryService.create_part(conn, request, actor_id=current_user.id)


@router.delete("/parts/{part_id}")
async def delete_part(
    part_id: UUID,
    current_user: CurrentUser = Depends(require_roles(["SYS_ADMIN", "FACILITIES_ADMIN"])),
):
    """
    Removes a part from inventory.
    """
    async with acquire_db_connection(
        actor_id=current_user.id,
        actor_role=current_user.role,
        dept_id=current_user.department_id,
    ) as conn:
        async with conn.transaction():
            await InventoryService.delete_part(conn, part_id)
            return {"success": True, "message": "Part deleted successfully."}


