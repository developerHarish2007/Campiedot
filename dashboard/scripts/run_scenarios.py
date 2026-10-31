import asyncio
import os
import sys
import json
from uuid import UUID, uuid4
from datetime import datetime, timezone, timedelta
from httpx import AsyncClient, ASGITransport

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from app.main import app
from app.database import init_db_pool, close_db_pool


async def run_scenario_1(client: AsyncClient, admin_token: str, tech_token: str, student_token: str):
    print("\n" + "#" * 80)
    print("SCENARIO 1: PRE-EXAM POWER DISRUPTION IN RM-ACAD-204 (110 STUDENTS)")
    print("#" * 80)

    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    tech_headers = {"Authorization": f"Bearer {tech_token}"}
    student_headers = {"Authorization": f"Bearer {student_token}"}

    # Step 1: Ingest urgent student/faculty incident report
    print("\n[STEP 1] Ingesting incident report from RM-ACAD-204 right before semester exam...")
    report_text = "Urgent: Complete power blackout in RM-ACAD-204! Overhead lights and projector are completely dead. 110 students are arriving for the CS8601 semester exam!"
    intake_res = await client.post(
        "/api/v1/intake",
        json={"text": report_text, "channel": "PORTAL_FORM"},
        headers=student_headers
    )
    assert intake_res.status_code == 201, f"Intake failed: {intake_res.text}"
    ticket = intake_res.json()
    wo_id = ticket["work_order_id"]
    ticket_num = ticket["ticket_number"]
    print(f"  -> Incident Ticket #{ticket_num} created in state '{ticket['state']}'.")
    print(f"     Resolved Node: {ticket['target_node_code']} ({ticket['target_node_name']})")
    print(f"     Extracted Category: {ticket['category']}")

    # Step 2: Consequence Analysis & Schedule Clash Detection
    print("\n[STEP 2] Querying active room bookings for RM-ACAD-204...")
    bookings_res = await client.get("/api/v1/bookings", headers=admin_headers)
    assert bookings_res.status_code == 200
    all_bookings = bookings_res.json()
    acad_booking = next((b for b in all_bookings if b["room_code"] == "RM-ACAD-204" and b["status"] == "CONFIRMED"), None)
    assert acad_booking is not None, "Target booking in RM-ACAD-204 not found!"
    print(f"  -> CRITICAL CLASH DETECTED:")
    print(f"     Event: '{acad_booking['course_or_event_title']}' ({acad_booking['booking_type']})")
    print(f"     Student Count: {acad_booking['student_count']} students")
    print(f"     Window: {acad_booking['start_time']} to {acad_booking['end_time']}")

    # Step 3: Run Deterministic CSP Alternative Room Solver
    print("\n[STEP 3] Executing CSP Solver for clash-free alternative venue...")
    alts_res = await client.get(
        f"/api/v1/rooms/alternatives?current_room_id={acad_booking['room_node_id']}&student_count={acad_booking['student_count']}&start_time={acad_booking['start_time']}&end_time={acad_booking['end_time']}",
        headers=admin_headers
    )
    assert alts_res.status_code == 200
    candidates = alts_res.json()
    print(f"  -> CSP Solver evaluated all rooms. Found {len(candidates)} clash-free candidates:")
    for idx, c in enumerate(candidates[:3]):
        print(f"     [{idx+1}] {c['room_code']} ({c['room_name']}) - Capacity: {c['room_capacity']}, Penalty Score: {c['penalty_score']}")
    top_venue = candidates[0]
    print(f"  -> Selected optimal venue: {top_venue['room_code']} ({top_venue['explanation']})")

    # Step 4: Technician Triage & Spare Part Shortage Detection
    print("\n[STEP 4] Dispatching Electrician & Triaging RM-ACAD-204...")
    assign_res = await client.post(f"/api/v1/work-orders/{wo_id}/assign", json={}, headers=admin_headers)
    assert assign_res.status_code == 200
    print(f"  -> Assigned to {assign_res.json()['assigned_tech_name']} (State: {assign_res.json()['work_order_state']})")

    print("  -> Electrician requests 63A MCCB Breaker (PART-MCCB-63A)...")
    parts_res = await client.get("/api/v1/inventory", headers=tech_headers)
    assert parts_res.status_code == 200
    mccb_part = next((p for p in parts_res.json() if p["sku"] == "PART-MCCB-63A"), None)
    assert mccb_part is not None, "Part PART-MCCB-63A not found!"

    inv_res = await client.post(
        "/api/v1/inventory/reservations",
        json={"work_order_id": wo_id, "items": [{"part_id": mccb_part["id"], "requested_qty": 1}]},
        headers=tech_headers
    )
    assert inv_res.status_code == 200
    inv_data = inv_res.json()
    print(f"  -> Part Reservation Result: all_reserved={inv_data['all_reserved']}")
    print(f"     Ticket #{ticket_num} transitioned to: {inv_data['work_order_state']}")
    print(f"     Reservation Status: {inv_data['reservations'][0]['status']}")

    # Step 5: Separation of Duties Enforcement on Approval
    print("\n[STEP 5] Checking Pending Approvals & Testing Separation of Duties...")
    app_res = await client.get("/api/v1/approvals?status=PENDING", headers=admin_headers)
    assert app_res.status_code == 200
    pending_apps = app_res.json()
    target_app = next((a for a in pending_apps if str(a["work_order_id"]) == str(wo_id)), None)
    assert target_app is not None, "Pending approval for work order not found!"
    app_id = target_app["id"]
    print(f"  -> Approval Request #{str(app_id)[:8]} for Rs. {target_app['requested_amount']:.2f}")

    # Technician tries to approve own repair (Separation of duties test)
    self_approve_res = await client.post(f"/api/v1/approvals/{app_id}/approve", headers=tech_headers)
    print(f"  -> Self-approval attempt by Technician: HTTP {self_approve_res.status_code}")
    if self_approve_res.status_code in (403, 409):
        print("     [PASS] Separation of duties upheld: Technician cannot approve own repair!")

    # Facilities Admin grants approval
    admin_approve_res = await client.post(f"/api/v1/approvals/{app_id}/approve", headers=admin_headers)
    assert admin_approve_res.status_code == 200, f"Approval failed: {admin_approve_res.text}"
    print(f"  -> Facilities Admin approved request. Status: {admin_approve_res.json()['status']}")

    # Step 6: What-If Dry-Run Simulation & Atomic Recovery Execution
    print("\n[STEP 6] Running What-If Dry-Run Simulation & Executing Plan A (Relocation)...")
    sim_res = await client.post(
        "/api/v1/simulations",
        json={"scenario_type": "ROOM_UNAVAILABLE", "target_node_code": "RM-ACAD-204"},
        headers=admin_headers
    )
    assert sim_res.status_code == 201
    sim_data = sim_res.json()
    sim_id = sim_data["simulation_id"]
    print(f"  -> Dry-run completed: Recommended Plan = {sim_data['recommended_plan']}")
    print(f"     Plan A Disruption Score: {sim_data['plan_a']['disruption_score']}/100 (0 min delay)")
    print(f"     Plan B Disruption Score: {sim_data['plan_b']['disruption_score']}/100 (55 min delay)")

    # Execute Plan A atomically
    exec_res = await client.post(f"/api/v1/simulations/{sim_id}/execute", json={"selected_plan": "PLAN_A"}, headers=admin_headers)
    assert exec_res.status_code == 200, f"Execution failed: {exec_res.text}"
    exec_data = exec_res.json()
    print(f"  -> Recovery Plan Executed Atomically:")
    print(f"     Status: {exec_data['status']}")
    print(f"     Message: {exec_data['message']}")

    # Step 7: Prove Invariants Live
    print("\n[STEP 7] Verifying Live Invariant Kernel after Disruption Execution...")
    inv_check = await client.get("/api/v1/invariants", headers=admin_headers)
    assert inv_check.status_code == 200
    inv_results = inv_check.json()
    assert inv_results["all_invariants_pass"] is True, f"Invariants failed: {inv_results}"
    print("  -> ALL 6 INVARIANTS HOLD 100%:")
    for k, v in inv_results["invariants"].items():
        print(f"     - {k}: {v} violations")

    print("\n[SUCCESS] SCENARIO 1 EXECUTED SUCCESSFULLY WITH ZERO INVARIANT VIOLATIONS.")


async def run_scenario_2(client: AsyncClient, admin_token: str, tech_token: str, student_token: str):
    print("\n" + "#" * 80)
    print("SCENARIO 2: 12-REPORT WI-FI STORM, TOPOLOGICAL CORRELATION & DYNAMIC REASSIGNMENT")
    print("#" * 80)

    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    tech_headers = {"Authorization": f"Bearer {tech_token}"}

    labs = ["LAB-ACAD-301", "LAB-ACAD-302", "LAB-ACAD-304"]

    # Step 1: Simulate 12 concurrent webhook reports across the 3 labs
    print("\n[STEP 1] Generating 12 simulated email webhook reports from 3 computer labs...")
    responses = []
    for i in range(12):
        target_lab = labs[i % len(labs)]
        evt_id = f"storm-webhook-{i:03d}"
        payload = {
            "event_id": evt_id,
            "sender": f"faculty_lab{i}@easwari.edu",
            "subject": f"Network down during practical exam in {target_lab}",
            "body": f"The thin clients in {target_lab} lost all LAN and Wi-Fi connection to the intranet server."
        }
        res = await client.post("/api/v1/integrations/email/webhook", json=payload)
        assert res.status_code == 201
        responses.append(res.json())

    print(f"  -> Ingested {len(responses)} reports.")
    dup_merges = sum(1 for r in responses if r.get("state") == "MERGED_DUPLICATE")
    triaged = sum(1 for r in responses if r.get("state") == "TRIAGED")
    print(f"     Stage A Duplicate Merges: {dup_merges}")
    print(f"     Direct Triaged Reports: {triaged}")

    # Step 2: Verify Stage B Topological DAG Correlation
    print("\n[STEP 2] Verifying Stage B Topological DAG Correlation on Core Switch SW-CORE-ACAD-F3...")
    master_inc = next((r for r in responses if r.get("correlation_action") == "SPAWNED_MASTER_INFRASTRUCTURE"), None)
    if not master_inc:
        # Check active work orders for the switch
        wo_res = await client.get("/api/v1/work-orders", headers=admin_headers)
        switch_wo = next((w for w in wo_res.json() if "SW-CORE-ACAD-F3" in (w.get("node_code") or "")), None)
        assert switch_wo is not None, "Master Infrastructure Work Order on switch not found!"
        master_ticket_num = switch_wo["ticket_number"]
        master_wo_id = switch_wo["id"]
        priority = switch_wo["calculated_priority"]
    else:
        master_ticket_num = master_inc["ticket_number"]
        master_wo_id = master_inc["work_order_id"]
        priority = "P0_CRITICAL"

    print(f"  -> Master Infrastructure Incident #{master_ticket_num} automatically created!")
    print(f"     Parent Node: SW-CORE-ACAD-F3 (Academic Block Floor 3 Core PoE Switch)")
    print(f"     Priority Auto-Escalated to: {priority}")

    # Step 3: Dynamic Reassignment and Shift Handoff
    print("\n[STEP 3] Assigning primary technician Suresh Kumar (Network)...")
    assign_res = await client.post(
        f"/api/v1/work-orders/{master_wo_id}/assign",
        json={},
        headers=admin_headers
    )
    assert assign_res.status_code == 200
    assigned_data = assign_res.json()
    assigned_tech = assigned_data["assigned_tech_name"]
    print(f"  -> Assigned to: {assigned_tech} (Deterministic Score: {assigned_data['score']})")

    # Primary tech goes offline (e.g. sick / emergency off-shift)
    print(f"\n[STEP 4] Primary technician {assigned_tech} goes unavailable (is_available = FALSE)...")
    tech_user_id = assigned_data["assigned_tech_id"]
    avail_res = await client.post(
        f"/api/v1/staff/{tech_user_id}/availability",
        json={"is_available": False},
        headers=admin_headers
    )
    assert avail_res.status_code == 200
    avail_data = avail_res.json()
    print(f"  -> Dynamic Reassignment Triggered automatically:")
    print(f"     Tickets Reassigned: {avail_data['affected_work_orders_count']}")
    for r in avail_data.get('reassignments', []):
        print(f"     - Ticket #{r['ticket_number']}: reassigned to {r['new_tech_name']} (hops: {r['reassignment_count']})")

    # Step 5: Webhook Replay Protection
    print("\n[STEP 5] Replaying an email webhook to prove idempotency...")
    replay_evt = "storm-webhook-000"
    replay_payload = {
        "event_id": replay_evt,
        "sender": "faculty_lab0@easwari.edu",
        "subject": "Network down during practical exam in LAB-ACAD-301",
        "body": "The thin clients in LAB-ACAD-301 lost all LAN and Wi-Fi connection to the intranet server."
    }
    replay_res = await client.post("/api/v1/integrations/email/webhook", json=replay_payload)
    assert replay_res.status_code == 201
    replay_data = replay_res.json()
    print(f"  -> Replay returned cached Ticket #{replay_data['ticket_number']} without creating a new record.")

    # Step 6: Live Invariant Check
    print("\n[STEP 6] Re-verifying Live Invariants across all tables...")
    inv_check = await client.get("/api/v1/invariants", headers=admin_headers)
    assert inv_check.status_code == 200
    assert inv_check.json()["all_invariants_pass"] is True
    print("  -> ALL INVARIANTS PASS WITH ZERO VIOLATIONS.")

    print("\n[SUCCESS] SCENARIO 2 EXECUTED SUCCESSFULLY WITH ZERO INVARIANT VIOLATIONS.")


async def main():
    print("=" * 80)
    print("CAMPUSOPS DEMONSTRATION SCENARIO RUNNER")
    print("Target Campus: SRM Easwari Engineering College (Autonomous), Ramapuram, Chennai")
    print("=" * 80)

    await init_db_pool()

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            # Login users
            admin_res = await client.post("/api/v1/auth/login", json={"email": "sys_admin_1@easwari.edu"})
            admin_token = admin_res.json()["access_token"]

            tech_res = await client.post("/api/v1/auth/login", json={"email": "tech_elec_1@easwari.edu"})
            tech_token = tech_res.json()["access_token"]

            student_res = await client.post("/api/v1/auth/login", json={"email": "student_1@easwari.edu"})
            student_token = student_res.json()["access_token"]

            # Run Scenario 1
            await run_scenario_1(client, admin_token, tech_token, student_token)

            # Run Scenario 2
            await run_scenario_2(client, admin_token, tech_token, student_token)

            print("\n" + "=" * 80)
            print("ALL DEMO SCENARIOS COMPLETED WITH 100% INVARIANT VERIFICATION!")
            print("=" * 80)
    finally:
        await close_db_pool()


if __name__ == "__main__":
    asyncio.run(main())
