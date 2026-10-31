import asyncio
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

import httpx

async def test_room_registration_feature():
    print("=" * 70)
    print("VERIFYING ROOM REGISTRATION FEATURE (CODE, NAME, CAPACITY, TYPE)")
    print("=" * 70)

    # Detect if live FastAPI server is running on port 8000
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
        # 1. Login as Administrator
        print("\n[1/4] Authenticating as System Administrator...")
        login_res = await client.post(
            "/api/v1/auth/login",
            json={"email": "sys_admin_1@easwari.edu", "password": "password123"}
        )
        assert login_res.status_code == 200, f"Login failed: {login_res.text}"
        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        print("  [PASS] Authenticated successfully.")

        # 2. Register New Room
        print("\n[2/4] Registering new smart laboratory...")
        room_payload = {
            "node_code": "LAB-ACAD-402",
            "name": "Cloud Computing & Cybersecurity Lab",
            "room_capacity": 75,
            "room_type": "LAB",
            "building_code": "EEC-ACAD",
            "floor_number": 4,
            "room_features": ["PROJECTOR", "AC", "COMPUTERS", "WIFI_AP"],
            "is_operational": True
        }
        res_post = await client.post("/api/v1/campus/rooms", json=room_payload, headers=headers)
        assert res_post.status_code == 201, f"Room creation failed: {res_post.text}"
        created_room = res_post.json()
        print(f"  [PASS] Created room {created_room['node_code']} (ID: {created_room['id']}):")
        print(f"         - Name: {created_room['name']}")
        print(f"         - Type: {created_room['room_type']}")
        print(f"         - Capacity: {created_room['room_capacity']} seats")
        print(f"         - Block: {created_room['building_code']}, Floor {created_room['floor_number']}")

        # 3. Duplicate rejection check
        print("\n[3/4] Testing duplicate room code collision protection...")
        res_dup = await client.post("/api/v1/campus/rooms", json=room_payload, headers=headers)
        assert res_dup.status_code == 409, f"Duplicate room should return 409 Conflict, got {res_dup.status_code}"
        print("  [PASS] Duplicate room code correctly rejected with HTTP 409 Conflict.")

        # 4. List rooms and verify presence
        print("\n[4/4] Verifying room appears in registered rooms registry...")
        res_list = await client.get("/api/v1/campus/rooms?building_code=EEC-ACAD", headers=headers)
        assert res_list.status_code == 200
        rooms = res_list.json()
        found = any(r["node_code"] == "LAB-ACAD-402" for r in rooms)
        assert found, "Created room not found in room listing!"
        print(f"  [PASS] Room LAB-ACAD-402 verified in EEC-ACAD registry ({len(rooms)} room in block).")

        # Clean up test room
        await client.delete(f"/api/v1/campus/rooms/{created_room['id']}", headers=headers)
        print("  [PASS] Test room cleaned up successfully.")

    finally:
        await client.aclose()
        if should_close_pool:
            from app.database import close_db_pool
            await close_db_pool()

    print("\n" + "=" * 70)
    print("ALL ROOM REGISTRATION CHECKS COMPLETED WITH 100% SUCCESS!")
    print("=" * 70)

if __name__ == "__main__":
    asyncio.run(test_room_registration_feature())
