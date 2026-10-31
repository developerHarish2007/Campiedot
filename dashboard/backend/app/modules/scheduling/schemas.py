from typing import Optional, List
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field


class BookingCreateRequest(BaseModel):
    room_node_id: UUID
    booking_type: str = Field(default="CLASS")  # CLASS, EXAM, MAINTENANCE_BLOCK, CONTINGENCY_HOLD
    course_or_event_title: str
    faculty_user_id: Optional[UUID] = None
    student_count: int = Field(default=30, ge=0)
    required_features: List[str] = Field(default_factory=list)
    start_time: datetime
    end_time: datetime
    linked_work_order_id: Optional[UUID] = None


class BookingResponse(BaseModel):
    id: UUID
    room_node_id: UUID
    room_code: Optional[str] = None
    room_name: Optional[str] = None
    building_code: Optional[str] = None
    booking_type: str
    course_or_event_title: str
    faculty_user_id: Optional[UUID] = None
    student_count: int
    required_features: List[str]
    start_time: datetime
    end_time: datetime
    status: str
    linked_work_order_id: Optional[UUID] = None
    relocated_to_booking_id: Optional[UUID] = None
    relocated_to_room_code: Optional[str] = None
    relocated_to_room_name: Optional[str] = None
    compromise_explanation: Optional[str] = None
    created_at: datetime


class RoomAlternativeResponse(BaseModel):
    room_id: UUID
    room_code: str
    room_name: str
    building_code: str
    floor_number: int
    room_capacity: int
    room_features: List[str]
    penalty_score: float
    is_same_building: bool
    floor_delta: int
    wasted_seats: int
    explanation: str


class RelocateBookingRequest(BaseModel):
    target_room_id: UUID
    reason: str = Field(default="Room relocated due to operational disruption.")



class RescheduleBookingRequest(BaseModel):
    target_room_id: UUID
    start_time: datetime
    end_time: datetime
    reason: str = Field(default="Class rescheduled by administrator.")
