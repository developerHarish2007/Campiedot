import asyncio
import os
import sys
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

import httpx

async def test_scheduling_feature():
    print("=" * 75)
    print("VERIFYING CLASS & UNDER-WORK MAINTENANCE SCHEDULING FEATURE")
    print("=" * 75)

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
        print("\n[1/6] Authenticating as System Administrator...")
        login_res = await client.post(
            "/api/v1/auth/login",
            json={"email": "sys_admin_1@easwari.edu", "password": "password123"}
        )
        assert login_res.status_code == 200, f"Login failed: {login_res.text}"
        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        print("  [PASS] Authenticated successfully.")

        # 2. Register a Room to test scheduling on (clean up existing bookings & room if exists)
        print("\n[2/6] Registering test room: RM-ACAD-305 (Data Analytics Hall)...")
        existing_rooms = await client.get("/api/v1/campus/rooms", headers=headers)
        for r in existing_rooms.json():
            if r["node_code"] == "RM-ACAD-305":
                # Delete any associated bookings first
                all_b = await client.get("/api/v1/bookings", headers=headers)
                for b in all_b.json():
                    if b["room_node_id"] == r["id"]:
                        await client.delete(f"/api/v1/bookings/{b['id']}", headers=headers)
                await client.delete(f"/api/v1/campus/rooms/{r['id']}", headers=headers)

        room_payload = {
            "node_code": "RM-ACAD-305",
            "name": "Data Analytics Hall",
            "room_capacity": 60,
            "room_type": "CLASSROOM",
            "building_code": "EEC-ACAD",
            "floor_number": 3,
            "room_features": ["AC", "PROJECTOR", "WIFI_AP"],
            "is_operational": True
        }
        res_room = await client.post("/api/v1/campus/rooms", json=room_payload, headers=headers)
        assert res_room.status_code in (200, 201), f"Room creation failed: {res_room.text}"
        room = res_room.json()
        room_id = room["id"]
        print(f"  [PASS] Created room {room['node_code']} (ID: {room_id})")

        # 3. Schedule "Under Work" Maintenance Window (10:00 to 12:00 UTC tomorrow)
        base_time = (datetime.now(timezone.utc) + timedelta(days=1)).replace(hour=10, minute=0, second=0, microsecond=0)
        maint_start = base_time.isoformat()
        maint_end = (base_time + timedelta(hours=2)).isoformat()

        print(f"\n[3/6] Scheduling 'Under Work' Maintenance Block ({maint_start} to {maint_end})...")
        maint_payload = {
            "room_node_id": room_id,
            "booking_type": "MAINTENANCE_BLOCK",
            "course_or_event_title": "AC Duct & Electrical Conduit Replacement",
            "student_count": 0,
            "start_time": maint_start,
            "end_time": maint_end,
        }
        res_maint = await client.post("/api/v1/bookings", json=maint_payload, headers=headers)
        assert res_maint.status_code in (200, 201), f"Maintenance schedule failed: {res_maint.text}"
        maint_booking = res_maint.json()
        maint_booking_id = maint_booking["id"]
        print(f"  [PASS] Successfully scheduled Under Work maintenance window! Booking ID: {maint_booking_id}")

        # 4. Attempt to schedule a Class during the Under Work window (11:00 to 13:00) -> Must trigger 409 Conflict
        clash_start = (base_time + timedelta(hours=1)).isoformat()
        clash_end = (base_time + timedelta(hours=3)).isoformat()
        print(f"\n[4/6] Attempting to schedule Class during Under Work window ({clash_start} to {clash_end})...")
        clash_payload = {
            "room_node_id": room_id,
            "booking_type": "CLASS",
            "course_or_event_title": "CS8401 - Database Management Systems",
            "student_count": 45,
            "start_time": clash_start,
            "end_time": clash_end,
        }
        res_clash = await client.post("/api/v1/bookings", json=clash_payload, headers=headers)
        print(f"  Received response code: {res_clash.status_code}")
        assert res_clash.status_code == 409, f"Expected 409 Conflict on overlap, got: {res_clash.status_code} - {res_clash.text}"
        err_msg = res_clash.json().get("message") or res_clash.json().get("detail") or res_clash.text
        print(f"  [PASS] Double-booking correctly prevented by GiST constraint! Error: {err_msg}")

        # 5. Schedule a non-overlapping Class (13:00 to 15:00) -> Must succeed
        free_start = (base_time + timedelta(hours=3)).isoformat()
        free_end = (base_time + timedelta(hours=5)).isoformat()
        print(f"\n[5/6] Scheduling non-overlapping Class after maintenance ({free_start} to {free_end})...")
        valid_payload = {
            "room_node_id": room_id,
            "booking_type": "CLASS",
            "course_or_event_title": "CS8401 - Database Management Systems",
            "student_count": 45,
            "start_time": free_start,
            "end_time": free_end,
        }
        res_valid = await client.post("/api/v1/bookings", json=valid_payload, headers=headers)
        assert res_valid.status_code in (200, 201), f"Valid class booking failed: {res_valid.text}"
        class_booking_id = res_valid.json()["id"]
        print(f"  [PASS] Successfully scheduled Class Lecture! Booking ID: {class_booking_id}")

        # 6. Release / Cancel the Maintenance Block
        print(f"\n[6/6] Releasing Under Work maintenance block (DELETE /api/v1/bookings/{maint_booking_id})...")
        res_del = await client.delete(f"/api/v1/bookings/{maint_booking_id}", headers=headers)
        assert res_del.status_code == 200, f"Cancel booking failed: {res_del.text}"
        print("  [PASS] Under Work window cancelled and released successfully.")

        # Cleanup class booking & test room
        await client.delete(f"/api/v1/bookings/{class_booking_id}", headers=headers)
        await client.delete(f"/api/v1/campus/rooms/{room_id}", headers=headers)
        print("\n  [CLEANUP] Test records cleanly purged.")

        print("\n" + "=" * 75)
        print("ALL SCHEDULING & UNDER-WORK TIMING VERIFICATIONS PASSED!")
        print("=" * 75)

    finally:
        await client.aclose()
        if should_close_pool:
            from app.database import close_db_pool
            await close_db_pool()

if __name__ == "__main__":
    asyncio.run(test_scheduling_feature())
