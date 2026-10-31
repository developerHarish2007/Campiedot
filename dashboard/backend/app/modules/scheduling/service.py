import json
from uuid import UUID
from typing import List, Optional, Dict, Any
from datetime import datetime
import asyncpg
from app.core.exceptions import ResourceNotFoundError, InvariantViolationError, CampusOpsException
from app.modules.scheduling.schemas import (
    BookingCreateRequest,
    BookingResponse,
    RoomAlternativeResponse,
)


class SchedulingService:

    @staticmethod
    async def check_unresolved_room_conflicts(conn: asyncpg.Connection) -> None:
        """
        Whenever an unresolved report exists in a classroom where a class/exam
        is scheduled within the next 3 hours (or active now), automatically:
        1. Marks the booking as IMPACTED_NEEDS_MOVE and links the work order.
        2. Elevates the work order to P0_CRITICAL.
        3. Generates AI alternative room suggestion.
        """
        try:
            conflict_rows = await conn.fetch(
                """
                SELECT rb.id AS booking_id, rb.room_node_id, rb.course_or_event_title,
                       rb.student_count, rb.required_features,
                       lower(rb.time_slot) AS start_time, upper(rb.time_slot) AS end_time,
                       wo.id AS work_order_id, wo.ticket_number, wo.partial_slots, wo.calculated_priority,
                       wo.reporter_user_id
                FROM room_bookings rb
                JOIN work_orders wo ON wo.target_node_id = rb.room_node_id
                WHERE rb.booking_type IN ('CLASS', 'EXAM')
                  AND rb.status = 'CONFIRMED'
                  AND wo.state NOT IN ('RESOLVED', 'CLOSED', 'MERGED_DUPLICATE')
                  AND (
                      (lower(rb.time_slot) <= NOW() + INTERVAL '3 hours' AND upper(rb.time_slot) >= NOW() - INTERVAL '30 minutes')
                      OR (lower(rb.time_slot) >= NOW() AND lower(rb.time_slot) <= NOW() + INTERVAL '3 hours')
                      OR (lower(rb.time_slot) <= NOW() AND upper(rb.time_slot) >= NOW())
                      OR (DATE(lower(rb.time_slot)) = CURRENT_DATE AND lower(rb.time_slot) <= NOW() + INTERVAL '3 hours')
                  );
                """
            )
            for row in conflict_rows:
                booking_id = row["booking_id"]
                wo_id = row["work_order_id"]

                raw_slots = row["partial_slots"]
                slots = json.loads(raw_slots) if isinstance(raw_slots, str) else (raw_slots or {})

                # If the class disruption has already been resolved/relocated by admin, skip re-escalating
                if slots.get("disrupted_class", {}).get("status") in ("RELOCATED", "SUSPENDED", "RESCHEDULED"):
                    continue

                # 1. Update booking
                await conn.execute(
                    """
                    UPDATE room_bookings 
                    SET status = 'IMPACTED_NEEDS_MOVE', linked_work_order_id = $1 
                    WHERE id = $2 AND status = 'CONFIRMED';
                    """,
                    wo_id, booking_id
                )

                # 2. Elevate work order to P0_CRITICAL
                if row["calculated_priority"] != "P0_CRITICAL":
                    await conn.execute(
                        """
                        UPDATE work_orders 
                        SET calculated_priority = 'P0_CRITICAL', reporter_urgency = 'P0_CRITICAL' 
                        WHERE id = $1;
                        """,
                        wo_id
                    )

                # 3. Compute AI prediction if not present
                if "disrupted_class" not in slots:
                    alternatives = await SchedulingService.find_alternative_rooms(
                        conn,
                        current_room_id=row["room_node_id"],
                        student_count=row["student_count"],
                        required_features=list(row["required_features"] or []),
                        start_time=row["start_time"],
                        end_time=row["end_time"]
                    )
                    if alternatives:
                        best_alt = alternatives[0]
                        impacted_node = await conn.fetchrow("SELECT node_code, name FROM campus_nodes WHERE id = $1;", row["room_node_id"])
                        slots["disrupted_class"] = {
                            "booking_id": str(booking_id),
                            "course_title": row["course_or_event_title"],
                            "student_count": row["student_count"],
                            "impacted_room_code": impacted_node["node_code"] if impacted_node else "Campus Room",
                            "impacted_room_name": impacted_node["name"] if impacted_node else "",
                            "recommended_room_id": str(best_alt.room_id),
                            "recommended_room_code": best_alt.room_code,
                            "recommended_room_name": best_alt.room_name,
                            "penalty_score": best_alt.penalty_score,
                            "ai_explanation": best_alt.explanation,
                            "start_time": row["start_time"].isoformat() if hasattr(row["start_time"], "isoformat") else str(row["start_time"]),
                            "end_time": row["end_time"].isoformat() if hasattr(row["end_time"], "isoformat") else str(row["end_time"]),
                        }
                        await conn.execute(
                            "UPDATE work_orders SET partial_slots = $1::jsonb WHERE id = $2;",
                            json.dumps(slots), wo_id
                        )

                        rec_room = best_alt.room_code
                        worker_alert = (
                            f"🚨 CRITICAL ESCALATION: Impending scheduled class '{row['course_or_event_title']}' "
                            f"starts within 3 hours in this room! Priority elevated to CRITICAL (P0). "
                            f"AI recommends relocating to {rec_room}. Immediate repair or admin relocation required."
                        )
                        await conn.execute(
                            """
                            INSERT INTO work_order_comments (work_order_id, author_user_id, author_name, author_role, message)
                            VALUES ($1, $2, 'Campus AI Dispatcher', 'SYS_ADMIN', $3);
                            """,
                            wo_id, row["reporter_user_id"], worker_alert
                        )
        except Exception as e:
            print(f"Error checking impending room conflicts: {e}")

    @staticmethod
    async def list_bookings(
        conn: asyncpg.Connection,
        room_node_id: Optional[UUID] = None,
        booking_type: Optional[str] = None,
        status: Optional[str] = None
    ) -> List[BookingResponse]:
        # Actively check for unresolved issues conflicting with upcoming classes in the next 3 hours
        await SchedulingService.check_unresolved_room_conflicts(conn)

        query = """
            SELECT rb.id, rb.room_node_id, cn.node_code AS room_code, cn.name AS room_name,
                   cn.building_code, rb.booking_type, rb.course_or_event_title,
                   rb.faculty_user_id, rb.student_count, rb.required_features,
                   lower(rb.time_slot) AS start_time, upper(rb.time_slot) AS end_time,
                   rb.status, rb.linked_work_order_id, rb.relocated_to_booking_id,
                   target_cn.node_code AS relocated_to_room_code,
                   target_cn.name AS relocated_to_room_name,
                   rb.compromise_explanation, rb.created_at
            FROM room_bookings rb
            JOIN campus_nodes cn ON cn.id = rb.room_node_id
            LEFT JOIN room_bookings target_rb ON target_rb.id = rb.relocated_to_booking_id
            LEFT JOIN campus_nodes target_cn ON target_cn.id = target_rb.room_node_id
            WHERE ($1::uuid IS NULL OR rb.room_node_id = $1)
              AND ($2::text IS NULL OR rb.booking_type = $2)
              AND ($3::text IS NULL OR rb.status = $3)
            ORDER BY lower(rb.time_slot) ASC;
        """
        rows = await conn.fetch(query, room_node_id, booking_type, status)
        return [
            BookingResponse(
                id=r["id"],
                room_node_id=r["room_node_id"],
                room_code=r["room_code"],
                room_name=r["room_name"],
                building_code=r["building_code"],
                booking_type=r["booking_type"],
                course_or_event_title=r["course_or_event_title"],
                faculty_user_id=r["faculty_user_id"],
                student_count=r["student_count"],
                required_features=list(r["required_features"] or []),
                start_time=r["start_time"],
                end_time=r["end_time"],
                status=r["status"],
                linked_work_order_id=r["linked_work_order_id"],
                relocated_to_booking_id=r["relocated_to_booking_id"],
                relocated_to_room_code=r["relocated_to_room_code"],
                relocated_to_room_name=r["relocated_to_room_name"],
                compromise_explanation=r["compromise_explanation"],
                created_at=r["created_at"]
            )
            for r in rows
        ]

    @staticmethod
    async def create_booking(
        conn: asyncpg.Connection,
        request: BookingCreateRequest,
        actor_id: Optional[UUID] = None
    ) -> BookingResponse:
        # Check node operational
        node = await conn.fetchrow("SELECT id, node_code, name, building_code, is_operational FROM campus_nodes WHERE id = $1;", request.room_node_id)
        if not node:
            raise ResourceNotFoundError("CampusNode", str(request.room_node_id))
        if not node["is_operational"] and request.booking_type in ('CLASS', 'EXAM', 'CONTINGENCY_HOLD'):
            raise InvariantViolationError("Room Booking Invariant", f"Cannot book room {node['node_code']} because it is non-operational.")

        faculty_id = request.faculty_user_id
        if request.booking_type in ('CLASS', 'EXAM') and not faculty_id:
            faculty_id = actor_id

        try:
            row = await conn.fetchrow(
                """
                INSERT INTO room_bookings (
                    room_node_id, booking_type, course_or_event_title,
                    faculty_user_id, student_count, required_features,
                    time_slot, status, linked_work_order_id
                )
                VALUES (
                    $1, $2, $3, $4, $5, $6,
                    tstzrange($7, $8, '[)'), 'CONFIRMED', $9
                )
                RETURNING id, room_node_id, booking_type, course_or_event_title,
                          faculty_user_id, student_count, required_features,
                          lower(time_slot) AS start_time, upper(time_slot) AS end_time,
                          status, linked_work_order_id, relocated_to_booking_id,
                          compromise_explanation, created_at;
                """,
                request.room_node_id,
                request.booking_type,
                request.course_or_event_title,
                faculty_id,
                request.student_count,
                request.required_features,
                request.start_time,
                request.end_time,
                request.linked_work_order_id
            )
        except asyncpg.exceptions.ExclusionViolationError as e:
            raise InvariantViolationError(
                "Room Double-Booking GiST Invariant",
                f"Room {node['node_code']} is already booked during the requested time window."
            )

        return BookingResponse(
            id=row["id"],
            room_node_id=row["room_node_id"],
            room_code=node["node_code"],
            room_name=node["name"],
            building_code=node["building_code"],
            booking_type=row["booking_type"],
            course_or_event_title=row["course_or_event_title"],
            faculty_user_id=row["faculty_user_id"],
            student_count=row["student_count"],
            required_features=list(row["required_features"] or []),
            start_time=row["start_time"],
            end_time=row["end_time"],
            status=row["status"],
            linked_work_order_id=row["linked_work_order_id"],
            relocated_to_booking_id=row["relocated_to_booking_id"],
            compromise_explanation=row["compromise_explanation"],
            created_at=row["created_at"]
        )

    @staticmethod
    async def find_alternative_rooms(
        conn: asyncpg.Connection,
        current_room_id: UUID,
        student_count: int,
        required_features: List[str],
        start_time: datetime,
        end_time: datetime
    ) -> List[RoomAlternativeResponse]:
        """
        Deterministic Constraint Satisfaction Problem (CSP) solver:
        Hard Constraints:
          - node_type == 'ROOM'
          - is_operational == TRUE
          - room_capacity >= student_count
          - room_features @> required_features
          - room_id <> current_room_id
          - NOT EXISTS overlapping active booking in time_slot
        Soft Scoring:
          - Building penalty: 0 if same building, +20.0 if different block
          - Floor delta penalty: abs(floor - current_floor) * 5.0
          - Wasted capacity penalty: (capacity - student_count) * 0.5
        """
        curr_room = await conn.fetchrow(
            "SELECT id, node_code, name, building_code, floor_number FROM campus_nodes WHERE id = $1;",
            current_room_id
        )
        if not curr_room:
            raise ResourceNotFoundError("CampusNode", str(current_room_id))

        curr_bldg = curr_room["building_code"]
        curr_floor = curr_room["floor_number"]

        query = """
            SELECT cn.id, cn.node_code, cn.name, cn.building_code, cn.floor_number,
                   cn.room_capacity, cn.room_features
            FROM campus_nodes cn
            WHERE cn.node_type = 'ROOM'
              AND COALESCE(cn.room_type, 'CLASSROOM') NOT IN ('ADMINISTRATIVE', 'FOOD_COURT')
              AND cn.is_operational = TRUE
              AND cn.room_capacity >= $1
              AND cn.room_features @> $2::text[]
              AND cn.id <> $3
              AND NOT EXISTS (
                  SELECT 1 FROM room_bookings rb
                  WHERE rb.room_node_id = cn.id
                    AND rb.status IN ('CONFIRMED', 'CONTINGENCY_HOLD', 'MAINTENANCE_BLOCK')
                    AND rb.time_slot && tstzrange($4, $5, '[)')
              )
            ORDER BY cn.room_capacity ASC;
        """
        candidates = await conn.fetch(query, student_count, required_features, current_room_id, start_time, end_time)

        results = []
        for cand in candidates:
            is_same = (cand["building_code"] == curr_bldg)
            bldg_pen = 0.0 if is_same else 20.0
            floor_delta = abs(cand["floor_number"] - curr_floor)
            floor_pen = floor_delta * 5.0
            wasted = cand["room_capacity"] - student_count
            wasted_pen = wasted * 0.5
            total_penalty = round(bldg_pen + floor_pen + wasted_pen, 2)

            b_target = cand["building_code"]
            loc_msg = "Same building" if is_same else f"Relocated from {curr_bldg} to {b_target}"
            explanation = f"{loc_msg}, Floor delta: {floor_delta}, Wasted seats: {wasted} (Score penalty: {total_penalty})."

            results.append(
                RoomAlternativeResponse(
                    room_id=cand["id"],
                    room_code=cand["node_code"],
                    room_name=cand["name"],
                    building_code=cand["building_code"],
                    floor_number=cand["floor_number"],
                    room_capacity=cand["room_capacity"],
                    room_features=list(cand["room_features"] or []),
                    penalty_score=total_penalty,
                    is_same_building=is_same,
                    floor_delta=floor_delta,
                    wasted_seats=wasted,
                    explanation=explanation
                )
            )

        # Sort by penalty ascending
        results.sort(key=lambda r: r.penalty_score)
        return results

    @staticmethod
    async def relocate_booking(
        conn: asyncpg.Connection,
        booking_id: UUID,
        target_room_id: UUID,
        actor_id: Optional[UUID] = None,
        reason: str = "Relocation executed due to operational disruption."
    ) -> BookingResponse:
        """
        Atomically relocates a confirmed booking to an alternative room.
        Transitions original booking to RELOCATED and creates target booking in CONFIRMED state.
        """
        orig = await conn.fetchrow(
            """
            SELECT id, room_node_id, booking_type, course_or_event_title,
                   faculty_user_id, student_count, required_features,
                   lower(time_slot) AS start_time, upper(time_slot) AS end_time,
                   status, linked_work_order_id
            FROM room_bookings
            WHERE id = $1
            FOR UPDATE;
            """,
            booking_id
        )
        if not orig:
            raise ResourceNotFoundError("RoomBooking", str(booking_id))

        if orig["status"] not in ('CONFIRMED', 'IMPACTED_NEEDS_MOVE'):
            raise InvariantViolationError("Booking Relocation", f"Booking {booking_id} has status {orig['status']} and cannot be relocated.")

        target_node = await conn.fetchrow(
            "SELECT id, node_code, name, building_code, is_operational, room_capacity FROM campus_nodes WHERE id = $1;",
            target_room_id
        )
        if not target_node:
            raise ResourceNotFoundError("CampusNode (Target Room)", str(target_room_id))

        if not target_node["is_operational"]:
            raise InvariantViolationError("Target Room Invariant", f"Target room {target_node['node_code']} is marked non-operational.")

        if target_node["room_capacity"] < orig["student_count"]:
            raise InvariantViolationError(
                "Capacity Invariant",
                f"Target room capacity ({target_node['room_capacity']}) is less than required student count ({orig['student_count']})."
            )

        # 1. Insert new booking (Target room is operational and healthy, so linked_work_order_id must be None)
        new_booking = await conn.fetchrow(
            """
            INSERT INTO room_bookings (
                room_node_id, booking_type, course_or_event_title,
                faculty_user_id, student_count, required_features,
                time_slot, status, linked_work_order_id, compromise_explanation
            )
            VALUES (
                $1, $2, $3, $4, $5, $6,
                tstzrange($7, $8, '[)'), 'CONFIRMED', NULL, $9
            )
            RETURNING id, room_node_id, booking_type, course_or_event_title,
                      faculty_user_id, student_count, required_features,
                      lower(time_slot) AS start_time, upper(time_slot) AS end_time,
                      status, linked_work_order_id, relocated_to_booking_id,
                      compromise_explanation, created_at;
            """,
            target_room_id,
            orig["booking_type"],
            orig["course_or_event_title"],
            orig["faculty_user_id"],
            orig["student_count"],
            orig["required_features"],
            orig["start_time"],
            orig["end_time"],
            f"Relocated from room {orig['room_node_id']}: {reason}"
        )

        # 2. Update original booking
        await conn.execute(
            """
            UPDATE room_bookings
            SET status = 'RELOCATED',
                relocated_to_booking_id = $2,
                compromise_explanation = $3
            WHERE id = $1;
            """,
            booking_id,
            new_booking["id"],
            f"Relocated to {target_node['node_code']} ({target_node['name']}): {reason}"
        )

        # 3. Mark work order partial_slots as RELOCATED so subsequent checks never re-flag it
        if orig["linked_work_order_id"]:
            wo = await conn.fetchrow(
                "SELECT id, partial_slots, reporter_user_id FROM work_orders WHERE id = $1;",
                orig["linked_work_order_id"]
            )
            if wo:
                raw = wo["partial_slots"]
                slots = json.loads(raw) if isinstance(raw, str) else (raw or {})
                if "disrupted_class" in slots:
                    slots["disrupted_class"]["status"] = "RELOCATED"
                    slots["disrupted_class"]["relocated_to_room_code"] = target_node["node_code"]
                    slots["disrupted_class"]["relocated_to_room_name"] = target_node["name"]
                    await conn.execute(
                        "UPDATE work_orders SET partial_slots = $1::jsonb WHERE id = $2;",
                        json.dumps(slots), orig["linked_work_order_id"]
                    )
                # Inform worker in comments
                await conn.execute(
                    """
                    INSERT INTO work_order_comments (work_order_id, author_user_id, author_name, author_role, message)
                    VALUES ($1, $2, 'Campus AI Dispatcher', 'SYS_ADMIN', $3);
                    """,
                    orig["linked_work_order_id"],
                    wo["reporter_user_id"],
                    f"Admin approved relocation: '{orig['course_or_event_title']}' moved to {target_node['node_code']} ({target_node['name']}). Disruption cleared."
                )

        # 4. Log audit
        await conn.execute(
            """
            INSERT INTO audit_logs (work_order_id, actor_user_id, action, previous_state, new_state, details)
            VALUES ($1, $2, 'BOOKING_RELOCATED', $3, 'RELOCATED', $4::jsonb);
            """,
            orig["linked_work_order_id"],
            actor_id,
            orig["status"],
            json.dumps({
                "original_booking_id": str(booking_id),
                "original_room_id": str(orig["room_node_id"]),
                "new_booking_id": str(new_booking["id"]),
                "new_room_id": str(target_room_id),
                "reason": reason
            })
        )

        return BookingResponse(
            id=new_booking["id"],
            room_node_id=new_booking["room_node_id"],
            room_code=target_node["node_code"],
            room_name=target_node["name"],
            building_code=target_node["building_code"],
            booking_type=new_booking["booking_type"],
            course_or_event_title=new_booking["course_or_event_title"],
            faculty_user_id=new_booking["faculty_user_id"],
            student_count=new_booking["student_count"],
            required_features=list(new_booking["required_features"] or []),
            start_time=new_booking["start_time"],
            end_time=new_booking["end_time"],
            status=new_booking["status"],
            linked_work_order_id=new_booking["linked_work_order_id"],
            relocated_to_booking_id=new_booking["relocated_to_booking_id"],
            compromise_explanation=new_booking["compromise_explanation"],
            created_at=new_booking["created_at"]
        )

    @staticmethod
    async def cancel_booking(conn: asyncpg.Connection, booking_id: UUID) -> bool:
        row = await conn.fetchrow("SELECT id FROM room_bookings WHERE id = $1;", booking_id)
        if not row:
            raise ResourceNotFoundError("RoomBooking", str(booking_id))
        await conn.execute("DELETE FROM room_bookings WHERE id = $1;", booking_id)
        return True

    @staticmethod
    async def suspend_booking(
        conn: asyncpg.Connection,
        booking_id: UUID,
        reason: str = "Class suspended by administrator."
    ) -> bool:
        row = await conn.fetchrow(
            "SELECT id, course_or_event_title, linked_work_order_id FROM room_bookings WHERE id = $1;",
            booking_id
        )
        if not row:
            raise ResourceNotFoundError("RoomBooking", str(booking_id))
        await conn.execute(
            """
            UPDATE room_bookings
            SET status = 'CANCELLED',
                compromise_explanation = $2
            WHERE id = $1;
            """,
            booking_id, reason
        )

        if row["linked_work_order_id"]:
            wo = await conn.fetchrow(
                "SELECT id, partial_slots, reporter_user_id FROM work_orders WHERE id = $1;",
                row["linked_work_order_id"]
            )
            if wo:
                raw = wo["partial_slots"]
                slots = json.loads(raw) if isinstance(raw, str) else (raw or {})
                if "disrupted_class" in slots:
                    slots["disrupted_class"]["status"] = "SUSPENDED"
                    await conn.execute(
                        "UPDATE work_orders SET partial_slots = $1::jsonb WHERE id = $2;",
                        json.dumps(slots), row["linked_work_order_id"]
                    )
                await conn.execute(
                    """
                    INSERT INTO work_order_comments (work_order_id, author_user_id, author_name, author_role, message)
                    VALUES ($1, $2, 'Campus AI Dispatcher', 'SYS_ADMIN', $3);
                    """,
                    row["linked_work_order_id"],
                    wo["reporter_user_id"],
                    f"Admin suspended class '{row['course_or_event_title']}' due to facility repair requirements."
                )

        return True

    @staticmethod
    async def reschedule_booking(
        conn: asyncpg.Connection,
        booking_id: UUID,
        target_room_id: UUID,
        start_time: datetime,
        end_time: datetime,
        reason: str = "Class rescheduled."
    ) -> BookingResponse:
        orig = await conn.fetchrow(
            """
            SELECT id, booking_type, course_or_event_title, faculty_user_id,
                   student_count, required_features, linked_work_order_id
            FROM room_bookings WHERE id = $1;
            """,
            booking_id
        )
        if not orig:
            raise ResourceNotFoundError("RoomBooking", str(booking_id))

        target_node = await conn.fetchrow(
            "SELECT id, node_code, name, building_code, is_operational, room_capacity FROM campus_nodes WHERE id = $1;",
            target_room_id
        )
        if not target_node:
            raise ResourceNotFoundError("CampusNode", str(target_room_id))

        # Update booking (unlink work order as this is now rescheduled)
        row = await conn.fetchrow(
            """
            UPDATE room_bookings
            SET room_node_id = $2,
                time_slot = tstzrange($3, $4, '[)'),
                status = 'CONFIRMED',
                linked_work_order_id = NULL,
                compromise_explanation = $5
            WHERE id = $1
            RETURNING id, room_node_id, booking_type, course_or_event_title,
                      faculty_user_id, student_count, required_features,
                      lower(time_slot) AS start_time, upper(time_slot) AS end_time,
                      status, linked_work_order_id, relocated_to_booking_id,
                      compromise_explanation, created_at;
            """,
            booking_id, target_room_id, start_time, end_time, reason
        )

        if orig["linked_work_order_id"]:
            wo = await conn.fetchrow(
                "SELECT id, partial_slots, reporter_user_id FROM work_orders WHERE id = $1;",
                orig["linked_work_order_id"]
            )
            if wo:
                raw = wo["partial_slots"]
                slots = json.loads(raw) if isinstance(raw, str) else (raw or {})
                if "disrupted_class" in slots:
                    slots["disrupted_class"]["status"] = "RESCHEDULED"
                    await conn.execute(
                        "UPDATE work_orders SET partial_slots = $1::jsonb WHERE id = $2;",
                        json.dumps(slots), orig["linked_work_order_id"]
                    )
                await conn.execute(
                    """
                    INSERT INTO work_order_comments (work_order_id, author_user_id, author_name, author_role, message)
                    VALUES ($1, $2, 'Campus AI Dispatcher', 'SYS_ADMIN', $3);
                    """,
                    orig["linked_work_order_id"],
                    wo["reporter_user_id"],
                    f"Admin rescheduled class '{orig['course_or_event_title']}' to {target_node['node_code']} ({target_node['name']})."
                )

        return BookingResponse(
            id=row["id"],
            room_node_id=row["room_node_id"],
            room_code=target_node["node_code"],
            room_name=target_node["name"],
            building_code=target_node["building_code"],
            booking_type=row["booking_type"],
            course_or_event_title=row["course_or_event_title"],
            faculty_user_id=row["faculty_user_id"],
            student_count=row["student_count"],
            required_features=list(row["required_features"] or []),
            start_time=row["start_time"],
            end_time=row["end_time"],
            status=row["status"],
            linked_work_order_id=row["linked_work_order_id"],
            relocated_to_booking_id=row["relocated_to_booking_id"],
            compromise_explanation=row["compromise_explanation"],
            created_at=row["created_at"]
        )
