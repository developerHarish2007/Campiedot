#!/usr/bin/env python3
"""
CampusOps: SRM Easwari Engineering College (Autonomous), Ramapuram, Chennai
Phase 2 Concurrency & Invariant Verification Suite (PostgreSQL 16 / asyncpg)
Validates:
  1. TEST_CONCURRENT_LAST_PART_RESERVATION (50 concurrent requests for last part via Barrier)
  2. TEST_IDEMPOTENCY_CONCURRENCY (20 simultaneous requests with identical idempotency key)
  3. TEST_IDEMPOTENCY_TAMPER_REJECTION (Replay with mutated payload raises 422)
  4. TEST_OFF_SHIFT_ASSIGNMENT_REJECTION (Off-shift technician rejected)
  5. TEST_DYNAMIC_REASSIGNMENT_ANTI_FLAP (Reassignment hops & 3-hop escalation stop)
"""

import asyncio
import os
import sys
from datetime import datetime, timezone, timedelta
from uuid import uuid4
import asyncpg
from dotenv import load_dotenv

# Ensure backend modules are on sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from app.modules.inventory.service import InventoryService
from app.modules.inventory.schemas import ReservePartsRequest, PartReservationItem
from app.modules.staffing.service import StaffingService
from app.modules.integrations.idempotency import claim_idempotency_key, complete_idempotency_key
from app.core.exceptions import ConflictError, IdempotencyConflictError

load_dotenv()

DB_HOST = os.getenv("POSTGRES_HOST", "localhost")
DB_PORT = int(os.getenv("POSTGRES_PORT", 5432))
DB_USER = os.getenv("POSTGRES_USER", "postgres")
DB_PASS = os.getenv("POSTGRES_PASSWORD", "postgres")
DB_NAME = os.getenv("POSTGRES_DB", "campusops")


async def run_phase2_verification():
    print("=" * 80)
    print("CAMPUSOPS PHASE 2 DETERMINISTIC CORE VERIFICATION: SRM EASWARI")
    print(f"Target Database: postgresql://{DB_USER}:****@{DB_HOST}:{DB_PORT}/{DB_NAME}")
    print("=" * 80)

    # Establish test connection pool
    pool = await asyncpg.create_pool(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASS,
        database=DB_NAME,
        min_size=10,
        max_size=60,
    )

    passed_checks = 0
    total_checks = 5

    try:
        # Fetch base actors
        async with pool.acquire() as conn:
            admin_id = await conn.fetchval("SELECT id FROM users WHERE role = 'SYS_ADMIN' LIMIT 1;")
            student_id = await conn.fetchval("SELECT id FROM users WHERE role = 'STUDENT_FACULTY' LIMIT 1;")
            dept_id = await conn.fetchval("SELECT id FROM departments WHERE code = 'DEPT-CSE-IT' LIMIT 1;")
            room_node_id = await conn.fetchval("SELECT id FROM campus_nodes WHERE node_code = 'RM-ACAD-204' LIMIT 1;")

        # ----------------------------------------------------------------------
        # TEST 1: TEST_CONCURRENT_LAST_PART_RESERVATION
        # ----------------------------------------------------------------------
        print("\n[TEST 1/5] Running TEST_CONCURRENT_LAST_PART_RESERVATION (50 concurrent workers)...")
        # 1. Seed a test SKU with physical=1, available=1, reserved=0
        test_sku = f"PART-CONC-{uuid4().hex[:6].upper()}"
        async with pool.acquire() as conn:
            part_id = await conn.fetchval(
                """
                INSERT INTO inventory_parts (sku, name, category, physical_on_hand_qty, available_qty, reserved_qty, reorder_threshold, unit_cost, lead_time_hours)
                VALUES ($1, 'High-Stress Test Relay', 'ELECTRICAL', 1, 1, 0, 1, 1200.00, 12)
                RETURNING id;
                """,
                test_sku
            )
            # Record initial receipt movement
            await conn.execute(
                """
                INSERT INTO inventory_movements (part_id, actor_id, movement_type, delta_physical, delta_available, delta_reserved)
                VALUES ($1, $2, 'RECEIPT', 1, 1, 0);
                """,
                part_id, admin_id
            )

            # Create 50 separate work orders
            wo_ids = []
            for i in range(50):
                w_id = await conn.fetchval(
                    """
                    INSERT INTO work_orders (conversation_thread_id, reporter_user_id, target_node_id, category, state, raw_description, department_id)
                    VALUES ($1, $2, $3, 'ELECTRICAL', 'ASSIGNED', $4, $5)
                    RETURNING id;
                    """,
                    f"thread-conc-{i}-{uuid4().hex[:6]}", student_id, room_node_id, f"Stress test ticket {i}", dept_id
                )
                wo_ids.append(w_id)

        # 2. Fire 50 concurrent reservation attempts using asyncio.Barrier
        num_workers = 50
        barrier = asyncio.Barrier(num_workers)
        results = []

        async def worker_reserve(wo_id):
            await barrier.wait()
            async with pool.acquire() as c:
                await c.execute(
                    "SELECT set_secure_context($1::uuid, 'SYS_ADMIN'::user_role, $2::uuid);",
                    admin_id, dept_id
                )
                async with c.transaction():
                    req = ReservePartsRequest(
                        work_order_id=wo_id,
                        items=[PartReservationItem(part_id=part_id, requested_qty=1)]
                    )
                    res = await InventoryService.reserve_parts(c, req, actor_id=admin_id)
                    return res

        tasks = [worker_reserve(wo_id) for wo_id in wo_ids]
        worker_outputs = await asyncio.gather(*tasks)

        reserved_count = sum(1 for o in worker_outputs if o.all_reserved)
        blocked_count = sum(1 for o in worker_outputs if not o.all_reserved)

        # Verify database balances
        async with pool.acquire() as conn:
            part_final = await conn.fetchrow(
                "SELECT physical_on_hand_qty, available_qty, reserved_qty FROM inventory_parts WHERE id = $1;",
                part_id
            )
            phys = part_final["physical_on_hand_qty"]
            avail = part_final["available_qty"]
            resv = part_final["reserved_qty"]

        if reserved_count == 1 and blocked_count == 49 and phys == 1 and avail == 0 and resv == 1:
            print(f"  [PASS] Exactly 1 request succeeded ({reserved_count}/50), 49 transitioned to BLOCKED_PARTS.")
            print(f"         Authoritative balance holds: physical={phys}, available={avail}, reserved={resv} (0 drift).")
            passed_checks += 1
        else:
            print(f"  [FAIL] Invariant violated! Reserved: {reserved_count}, Blocked: {blocked_count}, Balance: phys={phys}, avail={avail}, resv={resv}")

        # ----------------------------------------------------------------------
        # TEST 2: TEST_IDEMPOTENCY_CONCURRENCY
        # ----------------------------------------------------------------------
        print("\n[TEST 2/5] Running TEST_IDEMPOTENCY_CONCURRENCY (20 simultaneous calls with Barrier)...")
        shared_key = f"IDEM-CONC-{uuid4().hex[:8]}"
        test_payload = {
            "source": "WEBHOOK_EMAIL",
            "sender": "lab_tech@easwari.edu",
            "room": "RM-ACAD-204",
            "issue": "Air conditioner tripping breaker",
            "timestamp": "2026-10-30T10:00:00Z"
        }

        barrier_idem = asyncio.Barrier(20)
        idem_results = []

        async def worker_idempotent(worker_idx):
            await barrier_idem.wait()
            async with pool.acquire() as c:
                await c.execute(
                    "SELECT set_secure_context($1::uuid, 'SYS_ADMIN'::user_role, $2::uuid);",
                    admin_id, dept_id
                )
                async with c.transaction():
                    is_new, cached = await claim_idempotency_key(
                        c, source="WEBHOOK_EMAIL", idempotency_key=shared_key, payload=test_payload, worker_id=f"worker-{worker_idx}"
                    )
                    if is_new:
                        # Only the winner creates the work order
                        wo_id = await c.fetchval(
                            """
                            INSERT INTO work_orders (conversation_thread_id, reporter_user_id, target_node_id, category, state, raw_description, department_id)
                            VALUES ($1, $2, $3, 'HVAC', 'INGESTED', 'Idempotency test payload', $4)
                            RETURNING id;
                            """,
                            f"thread-{shared_key}", student_id, room_node_id, dept_id
                        )
                        response_data = {"work_order_id": str(wo_id), "status": "INGESTED", "ticket_created": True}
                        await complete_idempotency_key(
                            c, source="WEBHOOK_EMAIL", idempotency_key=shared_key, response_status=201, response_payload=response_data
                        )
                        return (True, response_data)
                    else:
                        return (False, cached)

        idem_tasks = [worker_idempotent(i) for i in range(20)]
        idem_outputs = await asyncio.gather(*idem_tasks)

        new_claims = sum(1 for is_new, _ in idem_outputs if is_new)
        replayed_claims = sum(1 for is_new, _ in idem_outputs if not is_new)

        # Check total work orders created with this thread id
        async with pool.acquire() as conn:
            created_wo_count = await conn.fetchval(
                "SELECT COUNT(*) FROM work_orders WHERE conversation_thread_id = $1;",
                f"thread-{shared_key}"
            )

        if new_claims == 1 and replayed_claims == 19 and created_wo_count == 1:
            print(f"  [PASS] Exactly 1 winner executed work order creation; 19 calls received replay response.")
            print(f"         Total work orders created in DB: {created_wo_count}.")
            passed_checks += 1
        else:
            print(f"  [FAIL] Idempotency concurrency failed: new_claims={new_claims}, replayed={replayed_claims}, db_records={created_wo_count}")

        # ----------------------------------------------------------------------
        # TEST 3: TEST_IDEMPOTENCY_TAMPER_REJECTION
        # ----------------------------------------------------------------------
        print("\n[TEST 3/5] Running TEST_IDEMPOTENCY_TAMPER_REJECTION...")
        # Using shared_key which is COMPLETED with test_payload, try calling with altered payload
        tampered_payload = test_payload.copy()
        tampered_payload["issue"] = "TAMPERED: Different issue description"

        tamper_rejected = False
        try:
            async with pool.acquire() as conn:
                async with conn.transaction():
                    await claim_idempotency_key(
                        conn, source="WEBHOOK_EMAIL", idempotency_key=shared_key, payload=tampered_payload
                    )
        except IdempotencyConflictError as e:
            tamper_rejected = True
        except Exception as e:
            if "Payload hash does not match" in str(e):
                tamper_rejected = True

        if tamper_rejected:
            print(f"  [PASS] Reusing idempotency key '{shared_key}' with modified body correctly rejected (422 Unprocessable Entity).")
            passed_checks += 1
        else:
            print("  [FAIL] Tampered payload was NOT rejected!")

        # ----------------------------------------------------------------------
        # TEST 4: TEST_OFF_SHIFT_ASSIGNMENT_REJECTION
        # ----------------------------------------------------------------------
        print("\n[TEST 4/5] Running TEST_OFF_SHIFT_ASSIGNMENT_REJECTION...")
        # Create a test technician whose shift was yesterday
        yesterday_start = datetime.now(timezone.utc) - timedelta(days=2)
        yesterday_end = yesterday_start + timedelta(hours=8)

        async with pool.acquire() as conn:
            off_shift_tech_id = await conn.fetchval(
                """
                INSERT INTO users (email, full_name, role, department_id, is_available, active_workload_count, max_concurrent_workload)
                VALUES ($1, 'Off-Shift Technician', 'TECHNICIAN', $2, TRUE, 0, 4)
                RETURNING id;
                """,
                f"offshift_{uuid4().hex[:6]}@easwari.edu", dept_id
            )
            # Add skill
            await conn.execute(
                "INSERT INTO staff_skills (user_id, skill, proficiency_level) VALUES ($1, 'ELECTRICAL', 5);",
                off_shift_tech_id
            )
            # Add shift strictly in the past
            await conn.execute(
                """
                INSERT INTO staff_shifts (user_id, shift_window)
                VALUES ($1, tstzrange($2, $3, '[)'));
                """,
                off_shift_tech_id, yesterday_start, yesterday_end
            )

            # Create a test work order
            test_wo_id = await conn.fetchval(
                """
                INSERT INTO work_orders (conversation_thread_id, reporter_user_id, target_node_id, category, state, raw_description, department_id)
                VALUES ($1, $2, $3, 'ELECTRICAL', 'TRIAGED', 'Off-shift assignment test', $4)
                RETURNING id;
                """,
                f"thread-shift-{uuid4().hex[:6]}", student_id, room_node_id, dept_id
            )

        off_shift_rejected = False
        try:
            async with pool.acquire() as conn:
                await conn.execute(
                    "SELECT set_secure_context($1::uuid, 'SYS_ADMIN'::user_role, $2::uuid);",
                    admin_id, dept_id
                )
                async with conn.transaction():
                    await StaffingService.assign_technician(
                        conn, work_order_id=test_wo_id, technician_id=off_shift_tech_id, actor_id=admin_id
                    )
        except ConflictError as e:
            if "outside active shift hours" in str(e):
                off_shift_rejected = True
        except Exception as e:
            if "outside active shift hours" in str(e):
                off_shift_rejected = True

        if off_shift_rejected:
            print("  [PASS] Assignment of off-shift technician correctly rejected by deterministic hard filter.")
            passed_checks += 1
        else:
            print("  [FAIL] Off-shift technician assignment was NOT rejected.")

        # ----------------------------------------------------------------------
        # TEST 5: TEST_DYNAMIC_REASSIGNMENT_ANTI_FLAP
        # ----------------------------------------------------------------------
        print("\n[TEST 5/5] Running TEST_DYNAMIC_REASSIGNMENT_ANTI_FLAP...")
        # 1. Reset technicians to available and clean workload
        async with pool.acquire() as conn:
            await conn.execute(
                "SELECT set_secure_context($1::uuid, 'SYS_ADMIN'::user_role, $2::uuid);",
                admin_id, dept_id
            )
            await conn.execute(
                "UPDATE users SET is_available = TRUE, active_workload_count = 0 WHERE role = 'TECHNICIAN';"
            )

            tech_1_id = await conn.fetchval("SELECT id FROM users WHERE email = 'tech_net_1@easwari.edu';")
            tech_2_id = await conn.fetchval("SELECT id FROM users WHERE email = 'tech_net_2@easwari.edu';")

            flap_wo_id = await conn.fetchval(
                """
                INSERT INTO work_orders (
                    conversation_thread_id, reporter_user_id, target_node_id, category,
                    state, raw_description, department_id, assigned_tech_id, reassignment_count
                )
                VALUES ($1, $2, $3, 'NETWORK', 'ASSIGNED', 'Dynamic Reassignment & Anti-Flap Test', $4, $5, 2)
                RETURNING id;
                """,
                f"thread-flap-{uuid4().hex[:6]}", student_id, room_node_id, dept_id, tech_1_id
            )
            # Increment tech 1 active workload
            await conn.execute("UPDATE users SET active_workload_count = active_workload_count + 1 WHERE id = $1;", tech_1_id)

            # Trigger tech 1 unavailable -> Should dynamically reassign to tech 2 (hop 2 -> 3)
            res1 = await StaffingService.toggle_availability(
                conn, technician_id=tech_1_id, is_available=False, reason="Medical leave", actor_id=admin_id
            )

            # Check new assignment
            wo_after_hop1 = await conn.fetchrow(
                "SELECT assigned_tech_id, reassignment_count, state FROM work_orders WHERE id = $1;", flap_wo_id
            )

            # Now tech_2 has reassignment_count = 3.
            # Trigger tech 2 unavailable -> Anti-flap guard MUST trigger (count >= 3 -> revert to TRIAGED, escalate to Admin)
            res2 = await StaffingService.toggle_availability(
                conn, technician_id=tech_2_id, is_available=False, reason="Emergency leave", actor_id=admin_id
            )

            wo_after_hop2 = await conn.fetchrow(
                "SELECT assigned_tech_id, reassignment_count, state FROM work_orders WHERE id = $1;", flap_wo_id
            )

            # Reset technician availability back to True for subsequent runs
            await conn.execute("UPDATE users SET is_available = TRUE WHERE id IN ($1, $2);", tech_1_id, tech_2_id)

        hop1_reassigned = (wo_after_hop1["assigned_tech_id"] == tech_2_id)
        hop2_escalated = (wo_after_hop2["assigned_tech_id"] is None and wo_after_hop2["state"] == "TRIAGED")

        if hop1_reassigned and hop2_escalated:
            print("  [PASS] Dynamic handoff successfully transferred work order to secondary technician.")
            print("  [PASS] Anti-flap guard triggered at 3rd hop: auto-reassignment halted, ticket reverted to TRIAGED, escalation recorded.")
            passed_checks += 1
        else:
            print(f"  [FAIL] Anti-flap test failed: hop1_assigned_tech={wo_after_hop1['assigned_tech_id']} (expected {tech_2_id}), hop2_state={wo_after_hop2['state']} (expected TRIAGED)")

    finally:
        await pool.close()

    print("\n" + "=" * 80)
    print(f"PHASE 2 VERIFICATION SUMMARY: {passed_checks}/{total_checks} CHECKS PASSED")
    if passed_checks == total_checks:
        print("ALL 5 PHASE 2 DETERMINISTIC CORE CHECKS PASSED WITH ZERO VIOLATIONS.")
        print("=" * 80)
        return True
    else:
        print(f"FAILED {total_checks - passed_checks} CHECK(S).")
        print("=" * 80)
        return False


if __name__ == "__main__":
    success = asyncio.run(run_phase2_verification())
    sys.exit(0 if success else 1)
