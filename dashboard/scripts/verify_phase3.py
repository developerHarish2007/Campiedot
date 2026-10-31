#!/usr/bin/env python3
"""
CampusOps: SRM Easwari Engineering College (Autonomous), Ramapuram, Chennai
Phase 3 AI Incident Intelligence & Topological Correlation Verification Suite
Tests:
  1. TEST_NLP_INTAKE_GROQ_EXTRACTION (Live Groq / fallback structured extraction)
  2. TEST_AMBIGUOUS_LOCATION_CLARIFICATION_LOOP (Floor-level ambiguity detection)
  3. TEST_STATEFUL_CLARIFICATION_REPLY_MERGE (Thread-bound slot merging without duplicate ticket creation)
  4. TEST_LLM_TIMEOUT_FALLBACK_PARSER (Deterministic regex parser validation)
  5. TEST_STAGE_A_DUPLICATE_MERGE (Exact room duplicate detection & counter increment)
  6. TEST_STAGE_B_TOPOLOGICAL_DAG_CORRELATION (Wi-Fi ticket storm correlated to SW-CORE-ACAD-F3)
  7. TEST_SIMULATED_EMAIL_WEBHOOK_IDEMPOTENCY (Replay protection & zero duplicate DB side effects)
"""

import asyncio
import os
import sys
from uuid import uuid4
from datetime import datetime, timezone
import asyncpg
from dotenv import load_dotenv

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from app.modules.intake.service import IntakeService
from app.modules.intake.schemas import InboundIntakeRequest, ClarificationReplyRequest
from app.modules.ai.fallback_parser import extract_deterministic_fallback

load_dotenv()

DB_HOST = os.getenv("POSTGRES_HOST", "localhost")
DB_PORT = int(os.getenv("POSTGRES_PORT", 5432))
DB_USER = os.getenv("POSTGRES_USER", "postgres")
DB_PASS = os.getenv("POSTGRES_PASSWORD", "postgres")
DB_NAME = os.getenv("POSTGRES_DB", "campusops")


async def run_phase3_verification():
    print("=" * 80)
    print("CAMPUSOPS PHASE 3 AI INCIDENT INTELLIGENCE & CORRELATION VERIFICATION")
    print(f"Target Database: postgresql://{DB_USER}:****@{DB_HOST}:{DB_PORT}/{DB_NAME}")
    print("=" * 80)

    pool = await asyncpg.create_pool(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASS,
        database=DB_NAME,
        min_size=5,
        max_size=20,
    )

    passed_checks = 0
    total_checks = 7

    try:
        async with pool.acquire() as conn:
            student_id = await conn.fetchval("SELECT id FROM users WHERE role = 'STUDENT_FACULTY' LIMIT 1;")
            admin_id = await conn.fetchval("SELECT id FROM users WHERE role = 'SYS_ADMIN' LIMIT 1;")
            dept_id = await conn.fetchval("SELECT id FROM departments WHERE code = 'DEPT-CSE-IT' LIMIT 1;")

            await conn.execute(
                "SELECT set_secure_context($1::uuid, 'SYS_ADMIN'::user_role, $2::uuid);",
                admin_id, dept_id
            )
            # Baseline cleanup: close active work orders from prior runs to guarantee deterministic isolation
            await conn.execute(
                "UPDATE work_orders SET state = 'CLOSED', updated_at = NOW() WHERE state NOT IN ('CLOSED', 'RESOLVED');"
            )

        # ----------------------------------------------------------------------
        # TEST 1: TEST_NLP_INTAKE_GROQ_EXTRACTION
        # ----------------------------------------------------------------------
        print("\n[TEST 1/7] Running TEST_NLP_INTAKE_GROQ_EXTRACTION...")
        test_text = "Projector lamp flickering and burning smell in RM-ACAD-204 right before the semester exam!"
        req1 = InboundIntakeRequest(
            text=test_text,
            conversation_thread_id=f"thread-groq-{uuid4().hex[:8]}",
            channel="PORTAL_FORM"
        )

        async with pool.acquire() as conn:
            await conn.execute("SELECT set_secure_context($1::uuid, 'STUDENT_FACULTY'::user_role, $2::uuid);", student_id, dept_id)
            async with conn.transaction():
                res1 = await IntakeService.process_intake(
                    conn, request=req1, reporter_id=student_id, actor_role="STUDENT_FACULTY"
                )

        t1_valid = (
            res1.category in ("AV_EQUIPMENT", "ELECTRICAL")
            and res1.target_node_code == "RM-ACAD-204"
            and res1.state == "TRIAGED"
            and not res1.clarification_needed
        )

        if t1_valid:
            print(f"  [PASS] Structured extraction successful ({res1.extractor_used}).")
            print(f"         Resolved Room: {res1.target_node_code}, Category: {res1.category}, State: {res1.state}.")
            passed_checks += 1
        else:
            print(f"  [FAIL] NLP extraction failed: cat={res1.category}, node={res1.target_node_code}, state={res1.state}")

        # ----------------------------------------------------------------------
        # TEST 2: TEST_AMBIGUOUS_LOCATION_CLARIFICATION_LOOP
        # ----------------------------------------------------------------------
        print("\n[TEST 2/7] Running TEST_AMBIGUOUS_LOCATION_CLARIFICATION_LOOP...")
        ambig_thread = f"thread-ambig-{uuid4().hex[:8]}"
        req2 = InboundIntakeRequest(
            text="Wi-Fi is completely dead in the 3rd floor lab, cannot load course materials.",
            conversation_thread_id=ambig_thread,
            channel="CHAT"
        )

        async with pool.acquire() as conn:
            await conn.execute("SELECT set_secure_context($1::uuid, 'STUDENT_FACULTY'::user_role, $2::uuid);", student_id, dept_id)
            async with conn.transaction():
                res2 = await IntakeService.process_intake(
                    conn, request=req2, reporter_id=student_id, actor_role="STUDENT_FACULTY"
                )

        t2_valid = (
            res2.state == "AWAITING_CLARIFICATION"
            and res2.clarification_needed
            and res2.clarification_question is not None
            and "candidate_rooms" in res2.partial_slots
            and any("LAB-ACAD-30" in c for c in res2.partial_slots["candidate_rooms"])
        )

        if t2_valid:
            print("  [PASS] Floor ambiguity detected (Floor 3 labs).")
            print(f"         Work order state: {res2.state}.")
            print(f"         Clarification Question: \"{res2.clarification_question}\"")
            passed_checks += 1
        else:
            print(f"  [FAIL] Clarification detection failed: state={res2.state}, needed={res2.clarification_needed}, q={res2.clarification_question}")

        # ----------------------------------------------------------------------
        # TEST 3: TEST_STATEFUL_CLARIFICATION_REPLY_MERGE
        # ----------------------------------------------------------------------
        print("\n[TEST 3/7] Running TEST_STATEFUL_CLARIFICATION_REPLY_MERGE...")
        reply_req = ClarificationReplyRequest(reply_text="I am specifically sitting in LAB-ACAD-301")

        async with pool.acquire() as conn:
            await conn.execute("SELECT set_secure_context($1::uuid, 'STUDENT_FACULTY'::user_role, $2::uuid);", student_id, dept_id)
            async with conn.transaction():
                res3 = await IntakeService.submit_clarification_reply(
                    conn, conversation_thread_id=ambig_thread, reply_text=reply_req.reply_text, reporter_id=student_id
                )

            # Check that total work orders on this thread is STILL EXACTLY 1
            wo_thread_count = await conn.fetchval(
                "SELECT COUNT(*) FROM work_orders WHERE conversation_thread_id = $1;", ambig_thread
            )

        t3_valid = (
            res3.state == "TRIAGED"
            and res3.target_node_code == "LAB-ACAD-301"
            and not res3.clarification_needed
            and wo_thread_count == 1
            and res3.work_order_id == res2.work_order_id
        )

        if t3_valid:
            print("  [PASS] User reply merged into existing slots on SAME work order (ID preserved).")
            print(f"         Transitioned to {res3.state} on resolved room {res3.target_node_code}. Total tickets on thread: {wo_thread_count}.")
            passed_checks += 1
        else:
            print(f"  [FAIL] Slot merge failed: state={res3.state}, room={res3.target_node_code}, count={wo_thread_count}")

        # ----------------------------------------------------------------------
        # TEST 4: TEST_LLM_TIMEOUT_FALLBACK_PARSER
        # ----------------------------------------------------------------------
        print("\n[TEST 4/7] Running TEST_LLM_TIMEOUT_FALLBACK_PARSER...")
        req4 = InboundIntakeRequest(
            text="Water pipe leakage flooding washroom in EEC-MAIN",
            conversation_thread_id=f"thread-fallback-{uuid4().hex[:8]}",
            channel="PORTAL_FORM"
        )

        async with pool.acquire() as conn:
            await conn.execute("SELECT set_secure_context($1::uuid, 'STUDENT_FACULTY'::user_role, $2::uuid);", student_id, dept_id)
            async with conn.transaction():
                res4 = await IntakeService.process_intake(
                    conn, request=req4, reporter_id=student_id, actor_role="STUDENT_FACULTY", force_fallback=True
                )

        t4_valid = (
            res4.category == "PLUMBING"
            and res4.target_node_code == "EEC-MAIN"
            and res4.extractor_used == "DETERMINISTIC_REGEX_FALLBACK"
            and res4.state == "TRIAGED"
        )

        if t4_valid:
            print(f"  [PASS] Deterministic fallback parser correctly extracted Category: {res4.category}, Node: {res4.target_node_code}.")
            print(f"         Extractor used: {res4.extractor_used}.")
            passed_checks += 1
        else:
            print(f"  [FAIL] Fallback parser failed: cat={res4.category}, node={res4.target_node_code}, extractor={res4.extractor_used}")

        # ----------------------------------------------------------------------
        # TEST 5: TEST_STAGE_A_DUPLICATE_MERGE
        # ----------------------------------------------------------------------
        print("\n[TEST 5/7] Running TEST_STAGE_A_DUPLICATE_MERGE...")
        dup_text = "Air conditioner completely stopped working in RM-ACAD-204"

        async with pool.acquire() as conn:
            await conn.execute("SELECT set_secure_context($1::uuid, 'STUDENT_FACULTY'::user_role, $2::uuid);", student_id, dept_id)
            # 1. First ticket
            async with conn.transaction():
                first_ticket = await IntakeService.process_intake(
                    conn,
                    request=InboundIntakeRequest(text=dup_text, conversation_thread_id=f"thread-dup1-{uuid4().hex[:6]}"),
                    reporter_id=student_id,
                    actor_role="STUDENT_FACULTY",
                    force_fallback=True
                )

            # 2. Second identical ticket within window
            async with conn.transaction():
                second_ticket = await IntakeService.process_intake(
                    conn,
                    request=InboundIntakeRequest(text=dup_text, conversation_thread_id=f"thread-dup2-{uuid4().hex[:6]}"),
                    reporter_id=student_id,
                    actor_role="STUDENT_FACULTY",
                    force_fallback=True
                )

            # Fetch reporter count on first ticket
            rep_count = await conn.fetchval(
                "SELECT correlator_reporter_count FROM work_orders WHERE id = $1;", first_ticket.work_order_id
            )

        t5_valid = (
            first_ticket.state == "TRIAGED"
            and second_ticket.state == "MERGED_DUPLICATE"
            and second_ticket.correlation_action == "MERGED_DUPLICATE"
            and rep_count == 2
        )

        if t5_valid:
            print("  [PASS] Stage A duplicate suppression verified.")
            print(f"         First Ticket: {first_ticket.state} (#{first_ticket.ticket_number})")
            print(f"         Second Ticket: {second_ticket.state} (#{second_ticket.ticket_number}) -> Merged into #{first_ticket.ticket_number}")
            print(f"         Master Reporter Count: {rep_count}.")
            passed_checks += 1
        else:
            print(f"  [FAIL] Duplicate merge failed: t1_state={first_ticket.state}, t2_state={second_ticket.state}, rep_count={rep_count}")

        # ----------------------------------------------------------------------
        # TEST 6: TEST_STAGE_B_TOPOLOGICAL_DAG_CORRELATION
        # ----------------------------------------------------------------------
        print("\n[TEST 6/7] Running TEST_STAGE_B_TOPOLOGICAL_DAG_CORRELATION (Wi-Fi storm)...")
        # Ingest Wi-Fi complaints from LAB-ACAD-301, LAB-ACAD-302, LAB-ACAD-304
        storm_labs = ["LAB-ACAD-301", "LAB-ACAD-302", "LAB-ACAD-304"]
        storm_responses = []

        async with pool.acquire() as conn:
            await conn.execute("SELECT set_secure_context($1::uuid, 'STUDENT_FACULTY'::user_role, $2::uuid);", student_id, dept_id)
            for lab in storm_labs:
                async with conn.transaction():
                    r = await IntakeService.process_intake(
                        conn,
                        request=InboundIntakeRequest(
                            text=f"No network or internet connectivity at all in {lab}",
                            conversation_thread_id=f"thread-storm-{lab}-{uuid4().hex[:6]}"
                        ),
                        reporter_id=student_id,
                        actor_role="STUDENT_FACULTY",
                        force_fallback=True
                    )
                    storm_responses.append(r)

            # Check if Master Infrastructure Incident on parent switch SW-CORE-ACAD-F3 was spawned
            master_switch_wo = await conn.fetchrow(
                """
                SELECT wo.id, wo.ticket_number, wo.state, wo.calculated_priority,
                       cn.node_code, wo.correlator_reporter_count
                FROM work_orders wo
                JOIN campus_nodes cn ON wo.target_node_id = cn.id
                WHERE cn.node_code = 'SW-CORE-ACAD-F3'
                  AND wo.category = 'NETWORK'
                  AND wo.state <> 'CLOSED'
                ORDER BY wo.created_at DESC
                LIMIT 1;
                """
            )

        t6_valid = (
            master_switch_wo is not None
            and master_switch_wo["node_code"] == "SW-CORE-ACAD-F3"
            and master_switch_wo["calculated_priority"] == "P0_CRITICAL"
        )

        if t6_valid:
            print("  [PASS] Stage B Topological DAG Correlation detected common failure point.")
            print(f"         Master Infrastructure Work Order #{master_switch_wo['ticket_number']} spawned on upstream core switch {master_switch_wo['node_code']}!")
            print(f"         Priority auto-escalated to: {master_switch_wo['calculated_priority']}.")
            passed_checks += 1
        else:
            print(f"  [FAIL] Topological correlation failed: master_wo={master_switch_wo}")

        # ----------------------------------------------------------------------
        # TEST 7: TEST_SIMULATED_EMAIL_WEBHOOK_IDEMPOTENCY
        # ----------------------------------------------------------------------
        print("\n[TEST 7/7] Running TEST_SIMULATED_EMAIL_WEBHOOK_IDEMPOTENCY...")
        shared_event_id = f"EMAIL-EVT-{uuid4().hex[:8]}"
        email_payload = InboundIntakeRequest(
            text="Subject: AC leaking water\nBody: In RM-MECH-102 the air conditioner is dripping water onto the floor.",
            conversation_thread_id=f"email-{shared_event_id}",
            idempotency_key=f"EMAIL-WEBHOOK-{shared_event_id}",
            channel="SIMULATED_EMAIL_WEBHOOK"
        )

        async with pool.acquire() as conn:
            await conn.execute("SELECT set_secure_context($1::uuid, 'STUDENT_FACULTY'::user_role, $2::uuid);", student_id, dept_id)
            # Call 1
            async with conn.transaction():
                res_email_1 = await IntakeService.process_intake(
                    conn, request=email_payload, reporter_id=student_id, actor_role="STUDENT_FACULTY", force_fallback=True
                )

            # Call 2 (Duplicate replay)
            async with conn.transaction():
                res_email_2 = await IntakeService.process_intake(
                    conn, request=email_payload, reporter_id=student_id, actor_role="STUDENT_FACULTY", force_fallback=True
                )

            # Check DB count
            total_email_tickets = await conn.fetchval(
                "SELECT COUNT(*) FROM work_orders WHERE conversation_thread_id = $1;", f"email-{shared_event_id}"
            )

        t7_valid = (
            total_email_tickets == 1
            and res_email_1.work_order_id == res_email_2.work_order_id
            and res_email_1.ticket_number == res_email_2.ticket_number
        )

        if t7_valid:
            print("  [PASS] Webhook replay protection verified: 0 duplicate database records created.")
            print(f"         First call returned ticket #{res_email_1.ticket_number}, second replay call returned identical ticket #{res_email_2.ticket_number}.")
            passed_checks += 1
        else:
            print(f"  [FAIL] Webhook idempotency failed: db_count={total_email_tickets}, id1={res_email_1.work_order_id}, id2={res_email_2.work_order_id}")

    finally:
        await pool.close()

    print("\n" + "=" * 80)
    print(f"PHASE 3 VERIFICATION SUMMARY: {passed_checks}/{total_checks} CHECKS PASSED")
    if passed_checks == total_checks:
        print("ALL 7 PHASE 3 AI INTELLIGENCE & CORRELATION CHECKS PASSED WITH ZERO VIOLATIONS.")
        print("=" * 80)
        return True
    else:
        print(f"FAILED {total_checks - passed_checks} CHECK(S).")
        print("=" * 80)
        return False


if __name__ == "__main__":
    success = asyncio.run(run_phase3_verification())
    sys.exit(0 if success else 1)
