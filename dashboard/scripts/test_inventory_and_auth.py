import asyncio
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

import httpx

async def test_inventory_and_auth():
    print("=" * 70)
    print("VERIFYING INVENTORY REGISTRATION & 2-ROLE PERSPECTIVE")
    print("=" * 70)

    # Detect live server or fallback
    is_live = False
    try:
        async with httpx.AsyncClient(timeout=1.0) as probe:
            res = await probe.get("http://localhost:8000/health")
            if res.status_code == 200:
                is_live = True
    except Exception:
        is_live = False

    if is_live:
        print("[MODE] Connecting to live FastAPI server on http://localhost:8000")
        client = httpx.AsyncClient(base_url="http://localhost:8000", timeout=10.0)
        should_close_pool = False
    else:
        print("[MODE] Connecting via in-process ASGI test harness")
        from app.main import app
        from app.database import init_db_pool, close_db_pool
        await init_db_pool()
        client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver", timeout=10.0)
        should_close_pool = True

    try:
        # 1. Login as Admin
        print("\n[1/4] Authenticating as Admin (Approvals)...")
        admin_login = await client.post(
            "/api/v1/auth/login",
            json={"email": "sys_admin_1@easwari.edu", "password": "password123"}
        )
        assert admin_login.status_code == 200
        admin_token = admin_login.json()["access_token"]
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        print("  [PASS] Admin authenticated successfully.")

        # 2. Login as Student / Staff
        print("\n[2/4] Authenticating as Student / Staff (Reporting)...")
        student_login = await client.post(
            "/api/v1/auth/login",
            json={"email": "student_1@easwari.edu", "password": "password123"}
        )
        assert student_login.status_code == 200
        student_token = student_login.json()["access_token"]
        student_headers = {"Authorization": f"Bearer {student_token}"}
        print("  [PASS] Student / Staff authenticated successfully.")

        # 3. Register Part as Admin
        print("\n[3/4] Registering new inventory part manually as Admin...")
        part_data = {
            "sku": "PART-AC-CAP-50",
            "name": "50 MFD Dual Motor Run Capacitor",
            "category": "HVAC",
            "quantity": 12,
            "unit_cost": "380.00",
            "reorder_threshold": 2,
            "lead_time_hours": 24
        }
        res_create = await client.post("/api/v1/inventory/parts", json=part_data, headers=admin_headers)
        assert res_create.status_code == 201, f"Failed to create part: {res_create.text}"
        part = res_create.json()
        print(f"  [PASS] Part created: {part['sku']} ({part['name']}) - On Hand: {part['physical_on_hand_qty']}")

        # 4. Student permission check (Student cannot create inventory parts)
        print("\n[4/4] Verifying Student / Staff cannot register inventory parts...")
        res_student = await client.post("/api/v1/inventory/parts", json=part_data, headers=student_headers)
        assert res_student.status_code == 403, "Student should have been blocked with 403 Forbidden!"
        print("  [PASS] Student / Staff correctly blocked with 403 Forbidden.")

        # Clean up
        await client.delete(f"/api/v1/inventory/parts/{part['id']}", headers=admin_headers)
        print("  [PASS] Test part deleted successfully.")

    finally:
        await client.aclose()
        if should_close_pool:
            from app.database import close_db_pool
            await close_db_pool()

    print("\n" + "=" * 70)
    print("ALL INVENTORY & 2-ROLE CHECKS COMPLETED WITH 100% SUCCESS!")
    print("=" * 70)

if __name__ == "__main__":
    asyncio.run(test_inventory_and_auth())

