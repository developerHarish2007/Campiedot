#!/usr/bin/env python3
"""
CampusOps: SRM Easwari Engineering College (Autonomous), Ramapuram, Chennai
Phase 1 Invariant Verification Suite (PostgreSQL 16 / asyncpg)
Validates the 6 Core Mathematical & Relational Invariants enforced by the Database Kernel.
"""

import asyncio
import os
import sys
from datetime import datetime, timezone, timedelta
import asyncpg
from dotenv import load_dotenv

load_dotenv()

DB_HOST = os.getenv("POSTGRES_HOST", "localhost")
DB_PORT = int(os.getenv("POSTGRES_PORT", 5432))
DB_USER = os.getenv("POSTGRES_USER", "postgres")
DB_PASS = os.getenv("POSTGRES_PASSWORD", "postgres")
DB_NAME = os.getenv("POSTGRES_DB", "campusops")


async def run_verification():
    print("=" * 80)
    print("CAMPUSOPS PHASE 1 INVARIANT KERNEL VERIFICATION: SRM EASWARI")
    print(f"Target Database: postgresql://{DB_USER}:****@{DB_HOST}:{DB_PORT}/{DB_NAME}")
    print("=" * 80)

    try:
        conn = await asyncpg.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASS,
            database=DB_NAME,
        )
    except Exception as e:
        print(f"[FATAL] Could not connect to PostgreSQL: {e}")
        print("Ensure PostgreSQL is running and credentials in .env are correct.")
        sys.exit(1)

    passed_checks = 0
    total_checks = 6

    try:
        # ----------------------------------------------------------------------
        # TEST 1: CHECK_TABLES_AND_VIEWS
        # ----------------------------------------------------------------------
        print("\n[TEST 1/6] Running CHECK_TABLES_AND_VIEWS...")
        required_tables = [
            "security_context_session", "departments", "users", "staff_shifts",
            "staff_skills", "campus_nodes", "node_dependencies", "processed_events",
            "inventory_parts", "inventory_movements", "work_orders", "part_reservations",
            "fsm_state_transitions", "approvals", "room_bookings", "audit_logs",
            "outbound_notifications"
        ]
        required_views = [
            "v_analytics_summary", "v_recurring_incidents", "v_staff_utilization",
            "v_inventory_shortages"
        ]

        existing_tables = await conn.fetch(
            """
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema = 'public' AND table_type = 'BASE TABLE';
            """
        )
        existing_table_names = {r["table_name"] for r in existing_tables}

        existing_views = await conn.fetch(
            """
            SELECT table_name FROM information_schema.views 
            WHERE table_schema = 'public';
            """
        )
        existing_view_names = {r["table_name"] for r in existing_views}

        missing_tables = [t for t in required_tables if t not in existing_table_names]
        missing_views = [v for v in required_views if v not in existing_view_names]

        if missing_tables or missing_views:
            print(f"  [FAIL] Missing tables: {missing_tables}, Missing views: {missing_views}")
        else:
            print(f"  [PASS] All {len(required_tables)} core relational tables and {len(required_views)} analytics views exist.")
            passed_checks += 1

        # ----------------------------------------------------------------------
        # TEST 2: CHECK_DAG_CYCLE_PREVENTION
        # ----------------------------------------------------------------------
        print("\n[TEST 2/6] Running CHECK_DAG_CYCLE_PREVENTION...")
        # Path in seed: SUBSTATION-MAIN -> PANEL-ACAD-F2 -> RM-ACAD-204 (ELECTRICAL)
        # Attempting reverse edge: RM-ACAD-204 -> SUBSTATION-MAIN (ELECTRICAL) creates a cycle!
        sub_id = await conn.fetchval("SELECT id FROM campus_nodes WHERE node_code = 'SUBSTATION-MAIN';")
        room_id = await conn.fetchval("SELECT id FROM campus_nodes WHERE node_code = 'RM-ACAD-204';")

        if not sub_id or not room_id:
            print("  [FAIL] Required nodes SUBSTATION-MAIN or RM-ACAD-204 not found in campus_nodes.")
        else:
            cycle_blocked = False
            try:
                async with conn.transaction():
                    await conn.execute(
                        """
                        INSERT INTO node_dependencies (parent_node_id, child_node_id, dependency_domain)
                        VALUES ($1, $2, 'ELECTRICAL');
                        """,
                        room_id, sub_id
                    )
            except asyncpg.exceptions.CheckViolationError as e:
                # Trigger raises exception with SQLSTATE 23514
                if "DAG Cycle Violation" in str(e):
                    cycle_blocked = True
            except Exception as e:
                if "DAG Cycle Violation" in str(e):
                    cycle_blocked = True
                else:
                    print(f"  [INFO] Unexpected exception on DAG cycle test: {e}")

            if cycle_blocked:
                print("  [PASS] Circular dependency (RM-ACAD-204 -> SUBSTATION-MAIN) correctly blocked by DAG acyclic trigger (SQLSTATE 23514).")
                passed_checks += 1
            else:
                print("  [FAIL] Circular dependency was NOT blocked by database trigger.")

        # ----------------------------------------------------------------------
        # TEST 3: CHECK_ROOM_DOUBLE_BOOKING
        # ----------------------------------------------------------------------
        print("\n[TEST 3/6] Running CHECK_ROOM_DOUBLE_BOOKING...")
        mech_room_id = await conn.fetchval("SELECT id FROM campus_nodes WHERE node_code = 'RM-MECH-102';")
        mgr_id = await conn.fetchval("SELECT id FROM users WHERE email = 'mgr_acad@easwari.edu';")

        test_start = datetime.now(timezone.utc) + timedelta(days=2, hours=10)
        test_end = test_start + timedelta(hours=2)
        overlap_start = test_start + timedelta(hours=1)
        overlap_end = test_start + timedelta(hours=3)

        double_booking_blocked = False
        try:
            async with conn.transaction():
                # 1. First booking succeeds
                await conn.execute(
                    """
                    INSERT INTO room_bookings (room_node_id, booking_type, course_or_event_title, faculty_user_id, student_count, time_slot, status)
                    VALUES ($1, 'CLASS', 'Test Booking Alpha', $2, 50, tstzrange($3, $4, '[)'), 'CONFIRMED');
                    """,
                    mech_room_id, mgr_id, test_start, test_end
                )

                # 2. Overlapping booking on same room MUST fail via GiST exclusion
                await conn.execute(
                    """
                    INSERT INTO room_bookings (room_node_id, booking_type, course_or_event_title, faculty_user_id, student_count, time_slot, status)
                    VALUES ($1, 'CLASS', 'Test Booking Beta Overlapping', $2, 60, tstzrange($3, $4, '[)'), 'CONFIRMED');
                    """,
                    mech_room_id, mgr_id, overlap_start, overlap_end
                )
        except asyncpg.exceptions.ExclusionViolationError as e:
            if "prevent_room_double_booking" in str(e):
                double_booking_blocked = True
        except Exception as e:
            if "prevent_room_double_booking" in str(e) or "exclusion" in str(e).lower():
                double_booking_blocked = True
            else:
                print(f"  [INFO] Unexpected exception on room double-booking test: {e}")

        if double_booking_blocked:
            print("  [PASS] Overlapping booking on RM-MECH-102 blocked by GiST Exclusion Constraint (prevent_room_double_booking).")
            passed_checks += 1
        else:
            print("  [FAIL] Overlapping room booking was NOT blocked by database GiST constraint.")

        # ----------------------------------------------------------------------
        # TEST 4: CHECK_INVENTORY_TAMPER_GUARD
        # ----------------------------------------------------------------------
        print("\n[TEST 4/6] Running CHECK_INVENTORY_TAMPER_GUARD...")
        part_id = await conn.fetchval("SELECT id FROM inventory_parts WHERE sku = 'PART-MCCB-63A';")

        tamper_blocked = False
        try:
            async with conn.transaction():
                # Direct balance modification without movement record MUST fail
                await conn.execute(
                    """
                    UPDATE inventory_parts 
                    SET available_qty = 99, physical_on_hand_qty = 99 
                    WHERE id = $1;
                    """,
                    part_id
                )
        except asyncpg.exceptions.RaiseError as e:
            if "Inventory Security Violation" in str(e):
                tamper_blocked = True
        except Exception as e:
            if "Inventory Security Violation" in str(e):
                tamper_blocked = True
            else:
                print(f"  [INFO] Unexpected exception on inventory tamper test: {e}")

        if tamper_blocked:
            print("  [PASS] Direct balance mutation without inventory_movements record blocked by tamper guard trigger.")
            passed_checks += 1
        else:
            print("  [FAIL] Direct inventory balance update was NOT blocked by tamper guard.")

        # ----------------------------------------------------------------------
        # TEST 5: CHECK_FSM_TRANSITION_GUARD
        # ----------------------------------------------------------------------
        print("\n[TEST 5/6] Running CHECK_FSM_TRANSITION_GUARD...")
        student_id = await conn.fetchval("SELECT id FROM users WHERE email = 'student_1@easwari.edu';")
        admin_id = await conn.fetchval("SELECT id FROM users WHERE email = 'sys_admin_1@easwari.edu';")
        dept_id = await conn.fetchval("SELECT id FROM departments WHERE code = 'DEPT-CSE-IT';")
        room_node = await conn.fetchval("SELECT id FROM campus_nodes WHERE node_code = 'RM-ACAD-204';")

        fsm_jump_blocked = False
        try:
            async with conn.transaction():
                # Set context as SYS_ADMIN to create initial ticket in INGESTED
                await conn.execute("SELECT set_secure_context($1, 'SYS_ADMIN'::user_role, $2);", admin_id, dept_id)
                wo_id = await conn.fetchval(
                    """
                    INSERT INTO work_orders (conversation_thread_id, reporter_user_id, target_node_id, category, state, raw_description)
                    VALUES ('thread-test-fsm-101', $1, $2, 'ELECTRICAL', 'INGESTED', 'Test FSM Ticket')
                    RETURNING id;
                    """,
                    student_id, room_node
                )

                # Now switch context to STUDENT_FACULTY and attempt direct illegal jump to RESOLVED
                await conn.execute("SELECT set_secure_context($1, 'STUDENT_FACULTY'::user_role, $2);", student_id, dept_id)
                await conn.execute(
                    """
                    UPDATE work_orders SET state = 'RESOLVED' WHERE id = $1;
                    """,
                    wo_id
                )
        except asyncpg.exceptions.RaiseError as e:
            if "FSM Violation" in str(e):
                fsm_jump_blocked = True
        except Exception as e:
            if "FSM Violation" in str(e):
                fsm_jump_blocked = True
            else:
                print(f"  [INFO] Unexpected exception on FSM transition test: {e}")

        if fsm_jump_blocked:
            print("  [PASS] Unauthorized state transition (INGESTED -> RESOLVED by STUDENT_FACULTY) blocked by FSM trigger.")
            passed_checks += 1
        else:
            print("  [FAIL] Unauthorized FSM state transition was NOT blocked.")

        # ----------------------------------------------------------------------
        # TEST 6: CHECK_AUDIT_IMMUTABILITY
        # ----------------------------------------------------------------------
        print("\n[TEST 6/6] Running CHECK_AUDIT_IMMUTABILITY...")
        audit_blocked = False
        try:
            async with conn.transaction():
                # Insert a test audit record
                audit_id = await conn.fetchval(
                    """
                    INSERT INTO audit_logs (actor_user_id, action, details)
                    VALUES ($1, 'TEST_AUDIT_ACTION', '{"test": true}'::jsonb)
                    RETURNING id;
                    """,
                    admin_id
                )

                # Attempt to DELETE from audit_logs MUST fail unconditionally
                await conn.execute("DELETE FROM audit_logs WHERE id = $1;", audit_id)
        except asyncpg.exceptions.RaiseError as e:
            if "audit_logs is append-only" in str(e):
                audit_blocked = True
        except Exception as e:
            if "audit_logs is append-only" in str(e):
                audit_blocked = True
            else:
                print(f"  [INFO] Unexpected exception on audit immutability test: {e}")

        if audit_blocked:
            print("  [PASS] Audit log deletion blocked by tamper guard trigger (audit_logs is append-only).")
            passed_checks += 1
        else:
            print("  [FAIL] Audit log deletion was NOT blocked by trigger.")

    finally:
        await conn.close()

    print("\n" + "=" * 80)
    print(f"VERIFICATION SUMMARY: {passed_checks}/{total_checks} CHECKS PASSED")
    if passed_checks == total_checks:
        print("ALL 6 INVARIANT CHECKS PASSED WITH ZERO VIOLATIONS.")
        print("=" * 80)
        return True
    else:
        print(f"FAILED {total_checks - passed_checks} CHECK(S).")
        print("=" * 80)
        return False


if __name__ == "__main__":
    success = asyncio.run(run_verification())
    sys.exit(0 if success else 1)

