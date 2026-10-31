import asyncio
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import httpx

async def test_multi_agent_resend():
    print("=" * 80)
    print("VERIFYING MULTI-AGENT PIPELINE & RESEND EMAIL DISPATCH")
    print("  1. Agent 1 (WorkerDispatchAgent) via Groq")
    print("  2. Agent 2 (InstructionAgent) for Emergency Life-Safety")
    print("  3. Agent 3 (AntiHallucinationAgent) Multi-Agent Grounding Auditor")
    print("  4. Resend API Email Dispatch (via RESEND_API_KEY)")
    print("=" * 80)

    from app.main import app
    from app.database import init_db_pool, close_db_pool
    from app.modules.ai.agents import (
        WorkerDispatchAgent,
        InstructionAgent,
        AntiHallucinationAgent,
        EmergencyInstructionsSchema,
    )
    from app.modules.integrations.resend_client import ResendEmailService

    await init_db_pool()
    client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver", timeout=15.0)

    try:
        # Step 1: Unit Test Agent 1 (WorkerDispatchAgent)
        print("\n[1/5] Testing Agent 1: WorkerDispatchAgent...")
        dispatch_email = await WorkerDispatchAgent.generate_dispatch_email(
            ticket_number=105,
            category="ELECTRICAL",
            raw_description="Main circuit breaker panel sparking and humming loudly in Academic Tech Block 2nd floor.",
            location_hint="EEC-ACAD-204",
            worker_name="Selvam R",
            worker_role="Electrician",
            urgency="P0_CRITICAL"
        )
        print(f"  [PASS] Subject: {dispatch_email.subject}")
        print(f"  [PASS] Tools recommended: {dispatch_email.tools_needed}")
        print(f"  [PASS] Safety precautions: {dispatch_email.safety_precautions[:2]}")
        assert "Electrician" in dispatch_email.html_body or "ELECTRICAL" in dispatch_email.subject or "Selvam" in dispatch_email.html_body

        # Step 2: Unit Test Agent 2 (InstructionAgent)
        print("\n[2/5] Testing Agent 2: InstructionAgent on fast-spreading fire emergency...")
        fire_incident = "Fire is catching fast everywhere in Academic Tech Block 3rd floor lab, smoke spreading into hallways!"
        assert InstructionAgent.is_emergency_incident(fire_incident) is True
        safety_inst = await InstructionAgent.generate_safety_instructions(
            raw_description=fire_incident,
            detected_building="EEC-ACAD",
            detected_room="LAB-ACAD-301"
        )
        print(f"  [PASS] Headline: {safety_inst.headline}")
        print(f"  [PASS] Threat Level: {safety_inst.threat_level}")
        print(f"  [PASS] Evacuation Route: {safety_inst.evacuation_route}")
        print(f"  [PASS] Assembly Point: {safety_inst.assembly_point}")
        print(f"  [PASS] Actions count: {len(safety_inst.immediate_actions)}")
        assert safety_inst.is_emergency is True
        assert "elevator" in str(safety_inst.immediate_actions).lower() or "elevator" in safety_inst.evacuation_route.lower()

        # Step 3: Unit Test Agent 3 (AntiHallucinationAgent)
        print("\n[3/5] Testing Agent 3: AntiHallucinationAgent with deliberate safety violations...")
        hallucinated_data = EmergencyInstructionsSchema(
            is_emergency=True,
            threat_level="CRITICAL_HAZARD",
            headline="FIRE",
            target_building="Nonexistent Tower 42",
            immediate_actions=["Please take the elevator downstairs", "Wait inside the classroom"],
            evacuation_route="Use the North Skybridge and elevators",
            assembly_point="Fictional Beach Front",
            emergency_contacts=[]
        )
        grounded = await AntiHallucinationAgent.verify_and_ground_emergency(hallucinated_data)
        print(f"  [PASS] Grounded Route: {grounded.evacuation_route}")
        print(f"  [PASS] Grounded Assembly: {grounded.assembly_point}")
        print(f"  [PASS] Sanitized Actions: {grounded.immediate_actions}")
        assert "elevator" not in grounded.evacuation_route.lower() or "do not" in grounded.evacuation_route.lower()
        assert "Central Sports Ground" in grounded.assembly_point or "Ground" in grounded.assembly_point

        # Step 4: Unit Test Resend Email Dispatch
        print("\n[4/5] Testing Resend Email API dispatch...")
        resend_res = await ResendEmailService.send_email(
            to_email="delivered@resend.dev",
            subject="[CampusOps] Urgent Work Order Dispatch #105",
            html_body=dispatch_email.html_body,
            text_body=dispatch_email.text_body
        )
        print(f"  [PASS] Resend Response: Success={resend_res['success']}, ID={resend_res['id']}")
        assert resend_res["success"] is True
        assert resend_res["id"] is not None

        # Step 5: End-to-End API Integration Test
        print("\n[5/5] Testing End-to-End API Integration...")
        # A. Login
        login_res = await client.post(
            "/api/v1/auth/login",
            json={"email": "sys_admin_1@easwari.edu", "password": "password123"}
        )
        headers = {"Authorization": f"Bearer {login_res.json()['access_token']}"}

        # B. Intake Fire Emergency Report -> Triggers Agent 2 & Agent 3
        print("  - Submitting emergency fire report...")
        intake_res = await client.post(
            "/api/v1/intake",
            json={
                "text": "URGENT: Fire is catching fast everywhere in Academic Tech Block 3rd floor lab near RM-ACAD-204!",
                "channel": "PORTAL_FORM"
            },
            headers=headers
        )
        assert intake_res.status_code in (200, 201), f"Intake failed: {intake_res.text}"
        intake_data = intake_res.json()
        print(f"  - Intake returned Ticket #{intake_data['ticket_number']}")
        print(f"  - Emergency instructions generated: {intake_data.get('emergency_instructions') is not None}")
        if intake_data.get("emergency_instructions"):
            em = intake_data["emergency_instructions"]
            print(f"    * Headline: {em.get('headline')}")
            print(f"    * Assembly Point: {em.get('assembly_point')}")

        wo_id = intake_data["work_order_id"]

        # C. Assign Worker -> Triggers Agent 1 & Agent 3 & Resend API
        print(f"  - Assigning worker Murugan P (Plumber) to ticket {wo_id}...")
        assign_res = await client.post(
            f"/api/v1/work-orders/{wo_id}/assign",
            json={
                "worker_name": "Murugan P",
                "worker_email": "murugan.plumber@easwari.edu",
                "worker_role": "PLUMBING"
            },
            headers=headers
        )
        assert assign_res.status_code == 200, f"Assign failed: {assign_res.text}"
        assign_data = assign_res.json()
        print(f"  - Worker assigned: {assign_data['assigned_tech_name']} ({assign_data.get('assigned_tech_role')})")
        print(f"  - Resend email dispatched: {assign_data.get('email_dispatched')}")
        print(f"  - Email dispatch ID: {assign_data.get('email_dispatch_id')}")
        print(f"  - Email Subject: {assign_data.get('email_subject')}")
        assert assign_data["assigned_tech_name"] == "Murugan P"
        assert assign_data.get("email_dispatched") is True
        assert assign_data.get("email_dispatch_id") is not None

        print("\n" + "=" * 80)
        print("ALL MULTI-AGENT & RESEND EMAIL VERIFICATIONS PASSED SUCCESSFULLY!")
        print("=" * 80)

    finally:
        await client.aclose()
        await close_db_pool()

if __name__ == "__main__":
    asyncio.run(test_multi_agent_resend())
