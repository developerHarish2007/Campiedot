from uuid import UUID
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, Query, status
from app.core.security import get_current_user, CurrentUser, require_roles
from app.database import acquire_db_connection
from app.modules.scheduling.schemas import (
    RescheduleBookingRequest,
    BookingCreateRequest,
    BookingResponse,
    RoomAlternativeResponse,
    RelocateBookingRequest,
)
from app.modules.scheduling.service import SchedulingService

router = APIRouter(prefix="", tags=["Room Scheduling & Relocation"])


@router.get("/bookings", response_model=List[BookingResponse])
async def list_bookings(
    room_node_id: Optional[UUID] = Query(None),
    booking_type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    current_user: CurrentUser = Depends(get_current_user),
):
    async with acquire_db_connection(
        actor_id=current_user.id,
        actor_role=current_user.role,
        dept_id=current_user.department_id,
    ) as conn:
        return await SchedulingService.list_bookings(
            conn, room_node_id=room_node_id, booking_type=booking_type, status=status
        )


@router.post("/bookings", response_model=BookingResponse, status_code=status.HTTP_201_CREATED)
async def create_booking(
    request: BookingCreateRequest,
    current_user: CurrentUser = Depends(require_roles(["SYS_ADMIN", "FACILITIES_ADMIN", "DEPT_MANAGER", "STUDENT_FACULTY"])),
):
    async with acquire_db_connection(
        actor_id=current_user.id,
        actor_role=current_user.role,
        dept_id=current_user.department_id,
    ) as conn:
        async with conn.transaction():
            return await SchedulingService.create_booking(
                conn, request=request, actor_id=current_user.id
            )


@router.get("/rooms/alternatives", response_model=List[RoomAlternativeResponse])
async def find_alternative_rooms(
    current_room_id: UUID = Query(...),
    student_count: int = Query(...),
    features: Optional[List[str]] = Query(None),
    start_time: datetime = Query(...),
    end_time: datetime = Query(...),
    current_user: CurrentUser = Depends(get_current_user),
):
    required_features = features or []
    async with acquire_db_connection(
        actor_id=current_user.id,
        actor_role=current_user.role,
        dept_id=current_user.department_id,
    ) as conn:
        return await SchedulingService.find_alternative_rooms(
            conn,
            current_room_id=current_room_id,
            student_count=student_count,
            required_features=required_features,
            start_time=start_time,
            end_time=end_time
        )


@router.post("/bookings/{id}/relocate", response_model=BookingResponse)
async def relocate_booking(
    id: UUID,
    request: RelocateBookingRequest,
    current_user: CurrentUser = Depends(require_roles(["SYS_ADMIN", "FACILITIES_ADMIN", "DEPT_MANAGER"])),
):
    async with acquire_db_connection(
        actor_id=current_user.id,
        actor_role=current_user.role,
        dept_id=current_user.department_id,
    ) as conn:
        async with conn.transaction():
            return await SchedulingService.relocate_booking(
                conn,
                booking_id=id,
                target_room_id=request.target_room_id,
                actor_id=current_user.id,
                reason=request.reason
            )


@router.delete("/bookings/{id}")
async def cancel_booking(
    id: UUID,
    current_user: CurrentUser = Depends(require_roles(["SYS_ADMIN", "FACILITIES_ADMIN", "DEPT_MANAGER", "STUDENT_FACULTY"])),
):
    """
    Cancels a booking or releases a maintenance block window.
    """
    async with acquire_db_connection(
        actor_id=current_user.id,
        actor_role=current_user.role,
        dept_id=current_user.department_id,
    ) as conn:
        async with conn.transaction():
            await SchedulingService.cancel_booking(conn, id)
            return {"success": True, "message": "Booking released/cancelled successfully."}


@router.post("/bookings/{id}/suspend")
async def suspend_booking(
    id: UUID,
    current_user: CurrentUser = Depends(require_roles(["SYS_ADMIN", "FACILITIES_ADMIN", "DEPT_MANAGER"])),
):
    """
    Suspends a scheduled class due to facility operational issues.
    """
    async with acquire_db_connection(
        actor_id=current_user.id,
        actor_role=current_user.role,
        dept_id=current_user.department_id,
    ) as conn:
        async with conn.transaction():
            await SchedulingService.suspend_booking(conn, id, reason=f"Class suspended by {current_user.full_name} ({current_user.role}).")
            return {"success": True, "message": "Scheduled class suspended successfully."}


@router.post("/bookings/{id}/reschedule", response_model=BookingResponse)
async def reschedule_booking(
    id: UUID,
    request: RescheduleBookingRequest,
    current_user: CurrentUser = Depends(require_roles(["SYS_ADMIN", "FACILITIES_ADMIN", "DEPT_MANAGER"])),
):
    """
    Reschedules a class to another classroom and/or class hour.
    """
    async with acquire_db_connection(
        actor_id=current_user.id,
        actor_role=current_user.role,
        dept_id=current_user.department_id,
    ) as conn:
        async with conn.transaction():
            return await SchedulingService.reschedule_booking(
                conn,
                booking_id=id,
                target_room_id=request.target_room_id,
                start_time=request.start_time,
                end_time=request.end_time,
                reason=request.reason,
            )
