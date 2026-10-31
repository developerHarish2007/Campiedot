from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Query, status
from app.core.security import get_current_user, CurrentUser
from app.database import acquire_db_connection
from app.modules.work_orders.schemas import (
    CreateWorkOrderCommentRequest,
    WorkOrderCommentOut,
    CreateWorkOrderRequest,
    TransitionWorkOrderRequest,
    WorkOrderOut,
    WorkOrderTransitionResponse,
)
from app.modules.work_orders.service import WorkOrderService

router = APIRouter(prefix="/work-orders", tags=["Work Orders & FSM"])


@router.post("", response_model=WorkOrderOut, status_code=status.HTTP_201_CREATED)
async def create_work_order(
    request: CreateWorkOrderRequest,
    current_user: CurrentUser = Depends(get_current_user),
):
    async with acquire_db_connection(
        actor_id=current_user.id,
        actor_role=current_user.role,
        dept_id=current_user.department_id,
    ) as conn:
        async with conn.transaction():
            return await WorkOrderService.create_work_order(
                conn,
                request=request,
                reporter_id=current_user.id,
                actor_role=current_user.role,
                department_id=current_user.department_id,
            )


@router.get("", response_model=List[WorkOrderOut])
async def list_work_orders(
    state: Optional[str] = Query(None, description="Filter by wo_state"),
    category: Optional[str] = Query(None, description="Filter by issue_category"),
    assigned_tech_id: Optional[UUID] = Query(None, description="Filter by assigned technician ID"),
    limit: int = Query(50, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    current_user: CurrentUser = Depends(get_current_user),
):
    async with acquire_db_connection(
        actor_id=current_user.id,
        actor_role=current_user.role,
        dept_id=current_user.department_id,
    ) as conn:
        return await WorkOrderService.list_work_orders(
            conn,
            state=state,
            category=category,
            assigned_tech_id=assigned_tech_id,
            limit=limit,
            offset=offset,
        )


@router.get("/{id}", response_model=WorkOrderOut)
async def get_work_order(
    id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
):
    async with acquire_db_connection(
        actor_id=current_user.id,
        actor_role=current_user.role,
        dept_id=current_user.department_id,
    ) as conn:
        return await WorkOrderService.get_work_order(conn, id)


@router.post("/{id}/transition", response_model=WorkOrderTransitionResponse)
@router.post("/{id}/transitions", response_model=WorkOrderTransitionResponse)
async def transition_work_order(
    id: UUID,
    request: TransitionWorkOrderRequest,
    current_user: CurrentUser = Depends(get_current_user),
):
    async with acquire_db_connection(
        actor_id=current_user.id,
        actor_role=current_user.role,
        dept_id=current_user.department_id,
    ) as conn:
        async with conn.transaction():
            return await WorkOrderService.transition_work_order(
                conn,
                work_order_id=id,
                request=request,
                actor_id=current_user.id,
                actor_role=current_user.role,
            )


@router.get("/{id}/comments", response_model=List[WorkOrderCommentOut])
async def list_work_order_comments(
    id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
):
    async with acquire_db_connection(
        actor_id=current_user.id,
        actor_role=current_user.role,
        dept_id=current_user.department_id,
    ) as conn:
        return await WorkOrderService.list_comments(conn, work_order_id=id)


@router.post("/{id}/comments", response_model=WorkOrderCommentOut, status_code=status.HTTP_201_CREATED)
async def add_work_order_comment(
    id: UUID,
    request: CreateWorkOrderCommentRequest,
    current_user: CurrentUser = Depends(get_current_user),
):
    async with acquire_db_connection(
        actor_id=current_user.id,
        actor_role=current_user.role,
        dept_id=current_user.department_id,
    ) as conn:
        async with conn.transaction():
            return await WorkOrderService.add_comment(
                conn,
                work_order_id=id,
                author_id=current_user.id,
                author_name=current_user.full_name,
                author_role=current_user.role,
                message=request.message,
            )
