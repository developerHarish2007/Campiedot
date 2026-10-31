import asyncio
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

import httpx

async def test_worker_assignment():
    print("=" * 70)
    print("VERIFYING WORKER ASSIGNMENT FEATURE (NAME, EMAIL, ROLE: ELECTRICIAN/PLUMBER)")
    print("=" * 70)

    from app.main import app
    from app.database import init_db_pool, close_db_pool
    await init_db_pool()
    client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver", timeout=10.0)

    try:
        # 1. Login as Admin
        print("\n[1/4] Authenticating as System Administrator...")
        login_res = await client.post(
            "/api/v1/auth/login",
            json={"email": "sys_admin_1@easwari.edu", "password": "password123"}
        )
        assert login_res.status_code == 200, f"Login failed: {login_res.text}"
        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        print("  [PASS] Authenticated.")

        # 2. Create a test incident / work order
        print("\n[2/4] Creating test work order...")
        intake_res = await client.post(
            "/api/v1/intake",
            json={"text": "Water pipeline burst in Ground Floor washroom near Academic block.", "channel": "PORTAL_FORM"},
            headers=headers
        )
        assert intake_res.status_code in (200, 201), f"Intake failed: {intake_res.text}"
        wo = intake_res.json()
        wo_id = wo.get("work_order_id") or wo.get("id")
        print(f"  [PASS] Work order created: #{wo['ticket_number']} (ID: {wo_id}, State: {wo['state']})")

        # 3. Assign Worker with custom Name, Email, and Role (Plumber)
        print("\n[3/4] Assigning Worker: Name='Murugan P', Email='murugan.plumber@easwari.edu', Role='PLUMBING' (Plumber)...")
        assign_payload = {
            "worker_name": "Murugan P",
            "worker_email": "murugan.plumber@easwari.edu",
            "worker_role": "PLUMBING"
        }
        assign_res = await client.post(f"/api/v1/work-orders/{wo_id}/assign", json=assign_payload, headers=headers)
        assert assign_res.status_code == 200, f"Assignment failed: {assign_res.text}"
        assign_data = assign_res.json()
        print(f"  [PASS] Assignment successful!")
        print(f"    Assigned Worker: {assign_data['assigned_tech_name']} <{assign_data['assigned_tech_email']}>")
        print(f"    Worker Role: {assign_data.get('assigned_tech_role')}")
        print(f"    Work Order State: {assign_data['work_order_state']}")
        assert assign_data["assigned_tech_name"] == "Murugan P"
        assert assign_data["assigned_tech_email"] == "murugan.plumber@easwari.edu"
        assert assign_data["work_order_state"] == "ASSIGNED"

        # 4. Fetch the Work Order and verify details
        print("\n[4/4] Fetching work order to verify technician details in response schema...")
        get_res = await client.get(f"/api/v1/work-orders/{wo_id}", headers=headers)
        assert get_res.status_code == 200, f"Get WO failed: {get_res.text}"
        wo_details = get_res.json()
        print(f"  [PASS] Work order retrieved successfully:")
        print(f"    Assigned Tech Name: {wo_details['assigned_tech_name']}")
        print(f"    Assigned Tech Email: {wo_details['assigned_tech_email']}")
        print(f"    Assigned Tech Role: {wo_details['assigned_tech_role']}")
        assert wo_details["assigned_tech_name"] == "Murugan P"
        assert wo_details["assigned_tech_email"] == "murugan.plumber@easwari.edu"
        assert wo_details["assigned_tech_role"] == "PLUMBING"

        # 5. Test another assignment with Electrician
        print("\n[Bonus] Reassigning to Electrician: Name='Selvam R', Email='selvam.electrician@easwari.edu', Role='ELECTRICAL'...")
        reassign_payload = {
            "worker_name": "Selvam R",
            "worker_email": "selvam.electrician@easwari.edu",
            "worker_role": "ELECTRICAL"
        }
        reassign_res = await client.post(f"/api/v1/work-orders/{wo_id}/assign", json=reassign_payload, headers=headers)
        assert reassign_res.status_code == 200, f"Reassignment failed: {reassign_res.text}"
        reassign_data = reassign_res.json()
        print(f"  [PASS] Reassigned to: {reassign_data['assigned_tech_name']} ({reassign_data['assigned_tech_role']})")
        assert reassign_data["assigned_tech_name"] == "Selvam R"

        print("\n" + "=" * 70)
        print("ALL WORKER ASSIGNMENT TESTS PASSED SUCCESSFULLY!")
        print("=" * 70)

    finally:
        await client.aclose()
        await close_db_pool()

if __name__ == "__main__":
    asyncio.run(test_worker_assignment())
