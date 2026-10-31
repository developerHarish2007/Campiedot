import asyncio
import os
import sys
from uuid import uuid4
import httpx

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

async def test_worker_registration():
    from app.main import app
    from app.database import init_db_pool, close_db_pool

    await init_db_pool()
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver", timeout=15.0) as client:
        print("\n--- 1. Authenticate as Admin ---")
        login_res = await client.post("/api/v1/auth/login", json={"email": "sys_admin_1@easwari.edu"})
        assert login_res.status_code == 200, f"Login failed: {login_res.text}"
        admin_token = login_res.json()["access_token"]
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        print("✓ Admin logged in")

        print("\n--- 2. List Workers (Should be empty initially) ---")
        list_res = await client.get("/api/v1/staff/workers", headers=admin_headers)
        assert list_res.status_code == 200
        workers = list_res.json()
        print(f"Current registered workers count: {len(workers)}")

        print("\n--- 3. Register Electrician Worker as Admin ---")
        new_worker = {
            "full_name": "Murugan P",
            "email": "murugan.electrician@easwari.edu",
            "role": "ELECTRICAL"
        }
        reg_res = await client.post("/api/v1/staff/workers", json=new_worker, headers=admin_headers)
        assert reg_res.status_code == 201, f"Worker registration failed: {reg_res.text}"
        worker_data = reg_res.json()
        print(f"✓ Registered worker: {worker_data['full_name']} ({worker_data['email']}), Role: {worker_data['role']}")
        worker_id = worker_data["id"]

        print("\n--- 4. Verify Worker in List ---")
        list_res2 = await client.get("/api/v1/staff/workers", headers=admin_headers)
        assert list_res2.status_code == 200
        workers2 = list_res2.json()
        assert any(w["id"] == worker_id for w in workers2)
        print(f"✓ Worker found in list: {len(workers2)} worker(s)")

        print("\n--- 5. Verify Student Cannot Register Worker (Role Guard) ---")
        student_login = await client.post("/api/v1/auth/login", json={"email": "student_1@easwari.edu"})
        student_token = student_login.json()["access_token"]
        student_headers = {"Authorization": f"Bearer {student_token}"}

        denied_res = await client.post("/api/v1/staff/workers", json={
            "full_name": "Unauthorized Worker",
            "email": "unauth@easwari.edu",
            "role": "PLUMBING"
        }, headers=student_headers)
        assert denied_res.status_code == 403, f"Expected 403 Forbidden, got {denied_res.status_code}"
        print("✓ Non-admin registration forbidden (403)")

        print("\n--- 6. Delete Worker as Admin ---")
        del_res = await client.delete(f"/api/v1/staff/workers/{worker_id}", headers=admin_headers)
        assert del_res.status_code == 204, f"Delete failed: {del_res.text}"
        print("✓ Worker deregistered successfully")

        list_res3 = await client.get("/api/v1/staff/workers", headers=admin_headers)
        assert not any(w["id"] == worker_id for w in list_res3.json())
        print("✓ Worker removed from roster")

        print("\nALL WORKER REGISTRATION TESTS PASSED!")

    await close_db_pool()

if __name__ == "__main__":
    asyncio.run(test_worker_registration())

