#!/usr/bin/env python3
"""
CampusOps: Reset Database and Schedule 6 Random Classes
Cleans all operational entries (work orders, comments, logs, bookings, notifications)
and creates 6 fresh scheduled academic classes across legitimate campus classrooms.
"""

import asyncio
import os
import random
from datetime import datetime, timedelta, timezone
import asyncpg
from dotenv import load_dotenv

load_dotenv()

DB_HOST = os.getenv("POSTGRES_HOST", "localhost")
DB_PORT = int(os.getenv("POSTGRES_PORT", 5432))
DB_USER = os.getenv("POSTGRES_USER", "postgres")
DB_PASS = os.getenv("POSTGRES_PASSWORD", "postgres")
DB_NAME = os.getenv("POSTGRES_DB", "campusops")

SAMPLE_COURSES = [
    ("CS8601 Mobile Computing & Android Architectures", 65, ["PROJECTOR", "AC", "WIFI"]),
    ("IT8501 Web Technology & Distributed Cloud Systems", 70, ["PROJECTOR", "WIFI"]),
    ("CS8491 Computer Architecture & Microprocessors", 80, ["PROJECTOR", "AC"]),
    ("EC8691 Embedded Systems & IoT Sensing Lab", 60, ["PROJECTOR", "WIFI", "AC"]),
    ("ME8492 Kinematics of Machinery & Simulation", 75, ["PROJECTOR"]),
    ("RO8501 Industrial Robotics & Autonomous Motion", 45, ["PROJECTOR", "AC", "WIFI"]),
    ("AI8402 Deep Learning & Neural Engineering", 85, ["PROJECTOR", "AC", "AUDIO_SYSTEM"]),
    ("EE8503 Power Electronics & High Voltage Systems", 65, ["PROJECTOR", "AC"]),
]


async def reset_and_schedule():
    print("=" * 70)
    print("CAMPUSOPS: RESET DATABASE & SCHEDULE 6 FRESH CLASSES")
    print(f"Connecting to postgresql://{DB_USER}:****@{DB_HOST}:{DB_PORT}/{DB_NAME}")
    print("=" * 70)

    conn = await asyncpg.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASS,
        database=DB_NAME,
    )

    try:
        # Step 1: Clean all operational transactional tables
        print("\n[1/5] Clearing all operational entries...")
        await conn.execute("DELETE FROM work_order_comments;")
        await conn.execute("DELETE FROM outbound_notifications;")
        await conn.execute("DELETE FROM processed_events;")
        await conn.execute("DELETE FROM approvals;")
        await conn.execute("DELETE FROM part_reservations;")
        await conn.execute("DELETE FROM room_bookings;")

        # Purge audit logs
        try:
            await conn.execute("ALTER TABLE audit_logs DISABLE TRIGGER trg_audit_tamper_guard_row;")
            await conn.execute("ALTER TABLE audit_logs DISABLE TRIGGER trg_audit_tamper_guard_stmt;")
            await conn.execute("DELETE FROM audit_logs;")
            await conn.execute("ALTER TABLE audit_logs ENABLE TRIGGER trg_audit_tamper_guard_row;")
            await conn.execute("ALTER TABLE audit_logs ENABLE TRIGGER trg_audit_tamper_guard_stmt;")
        except Exception as e:
            print(f"  Note on audit logs: {e}")

        # Delete work orders
        await conn.execute("UPDATE work_orders SET parent_master_wo_id = NULL;")
        await conn.execute("DELETE FROM work_orders;")

        # Reset inventory
        try:
            await conn.execute("ALTER TABLE inventory_parts DISABLE TRIGGER trg_inventory_tamper_guard;")
            await conn.execute(
                """
                UPDATE inventory_parts
                SET reserved_qty = 0,
                    available_qty = physical_on_hand_qty;
                """
            )
            await conn.execute("ALTER TABLE inventory_parts ENABLE TRIGGER trg_inventory_tamper_guard;")
        except Exception as e:
            print(f"  Note on inventory: {e}")

        # Reset technician workload
        await conn.execute("UPDATE users SET active_workload_count = 0;")
        print("  + All work orders, comments, logs, and previous bookings purged.")

        # Step 2: Fetch eligible classroom nodes
        print("\n[2/5] Fetching classroom nodes...")
        rooms = await conn.fetch(
            """
            SELECT id, node_code, name, building_code, room_capacity, room_type
            FROM campus_nodes
            WHERE node_type = 'ROOM'
              AND (
                  room_type = 'CLASSROOM'
                  OR (
                      building_code IN ('EEC-ACAD', 'EEC-MECH-PG', 'EEC-ROBOTICS')
                      AND (room_type IS NULL OR room_type NOT IN ('AUDITORIUM', 'FOOD_COURT', 'ADMINISTRATIVE'))
                  )
              )
            ORDER BY RANDOM();
            """
        )

        if len(rooms) < 6:
            # Fallback to any room
            rooms = await conn.fetch("SELECT id, node_code, name, building_code, room_capacity, room_type FROM campus_nodes WHERE node_type = 'ROOM' ORDER BY RANDOM();")

        selected_rooms = rooms[:6]
        print(f"  + Selected {len(selected_rooms)} distinct classrooms:")
        for r in selected_rooms:
            print(f"    - {r['node_code']} ({r['name']}, {r['building_code']})")

        # Step 3: Fetch a faculty user for booking owner
        faculty = await conn.fetchrow(
            """
            SELECT id FROM users
            WHERE role IN ('STUDENT_FACULTY', 'DEPT_MANAGER', 'SYS_ADMIN')
            ORDER BY id ASC LIMIT 1;
            """
        )
        faculty_id = faculty["id"] if faculty else None

        # Step 4: Schedule 6 random classes with strategic timing relative to NOW
        print("\n[3/5] Scheduling 6 random academic classes...")
        now = datetime.now(timezone.utc)

        # Diverse timing schedule:
        # Class 1: Impending in 45 minutes (within 3h window)
        # Class 2: Impending in 1 hour 30 minutes (within 3h window)
        # Class 3: Impending in 2 hours 15 minutes (within 3h window)
        # Class 4: Currently in session (started 30 mins ago, ends in 1 hour)
        # Class 5: Later today in 4 hours
        # Class 6: Later today in 5 hours 30 minutes
        time_offsets = [
            (timedelta(minutes=45), timedelta(hours=2, minutes=45)),
            (timedelta(hours=1, minutes=30), timedelta(hours=3, minutes=30)),
            (timedelta(hours=2, minutes=15), timedelta(hours=4, minutes=15)),
            (-timedelta(minutes=30), timedelta(hours=1, minutes=30)),
            (timedelta(hours=4), timedelta(hours=6)),
            (timedelta(hours=5, minutes=30), timedelta(hours=7, minutes=30)),
        ]

        random_courses = random.sample(SAMPLE_COURSES, k=6)

        for i, room in enumerate(selected_rooms):
            course_title, default_students, features = random_courses[i]
            cap = room["room_capacity"] if room["room_capacity"] and room["room_capacity"] > 20 else 75
            student_count = min(default_students, cap)

            start_offset, end_offset = time_offsets[i]
            class_start = now + start_offset
            class_end = now + end_offset

            row = await conn.fetchrow(
                """
                INSERT INTO room_bookings (
                    room_node_id, booking_type, course_or_event_title,
                    faculty_user_id, student_count, required_features,
                    time_slot, status
                )
                VALUES ($1, 'CLASS', $2, $3, $4, $5, tstzrange($6, $7, '[)'), 'CONFIRMED')
                RETURNING id;
                """,
                room["id"],
                course_title,
                faculty_id,
                student_count,
                features,
                class_start,
                class_end,
            )

            relative_label = "in 45m" if i == 0 else "in 1.5h" if i == 1 else "in 2.25h" if i == 2 else "ACTIVE NOW" if i == 3 else f"in {start_offset.total_seconds()//3600:.1f}h"
            print(f"  + [{i+1}/6] {room['node_code']}: '{course_title}' ({student_count} students) -> {class_start.strftime('%H:%M')} - {class_end.strftime('%H:%M')} UTC ({relative_label})")

        # Step 5: Verify clean counts
        print("\n[4/5] Verifying database records...")
        wo_count = await conn.fetchval("SELECT COUNT(*) FROM work_orders;")
        booking_count = await conn.fetchval("SELECT COUNT(*) FROM room_bookings;")
        audit_count = await conn.fetchval("SELECT COUNT(*) FROM audit_logs;")

        print(f"  - Active Work Orders:  {wo_count} (Clean)")
        print(f"  - Scheduled Classes:   {booking_count} (Fresh 6 classes)")
        print(f"  - Audit Log Rows:      {audit_count}")

        print("\n" + "=" * 70)
        print("DATABASE RESET & RANDOM 6 CLASS SCHEDULING COMPLETE!")
        print("=" * 70)

    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(reset_and_schedule())
