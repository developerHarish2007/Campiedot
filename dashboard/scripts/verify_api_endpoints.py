import asyncio
import os
import sys
from datetime import datetime, timezone, timedelta
from httpx import AsyncClient, ASGITransport

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from app.main import app
from app.database import init_db_pool, close_db_pool


async def verify_endpoints():
    print("=" * 80)
    print("VERIFYING CAMPUSOPS FASTAPI HTTP ENDPOINTS & ADVANCED MODULES")
    print("=" * 80)

    await init_db_pool()

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            # 1. Health check
            print("\n[1/8] Testing GET /health...")
            res = await client.get("/health")
            assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
            data = res.json()
            print(f"  [PASS] Status: {data['status']}, Campus: {data['campus']}, Coords: {data['coordinates']}")

            # 2. Login to get Bearer token
            print("\n[2/8] Testing POST /api/v1/auth/login...")
            login_res = await client.post("/api/v1/auth/login", json={"email": "sys_admin_1@easwari.edu"})
            assert login_res.status_code == 200, f"Expected 200, got {login_res.status_code}: {login_res.text}"
            token = login_res.json()["access_token"]
            headers = {"Authorization": f"Bearer {token}"}
            print(f"  [PASS] Authenticated as {login_res.json()['full_name']} ({login_res.json()['role']})")

            # 3. Live Invariants Proof Endpoint
            print("\n[3/8] Testing GET /api/v1/invariants...")
            res_inv = await client.get("/api/v1/invariants", headers=headers)
            assert res_inv.status_code == 200, f"Expected 200, got {res_inv.status_code}: {res_inv.text}"
            inv_data = res_inv.json()
            print(f"  [PASS] Live Invariants Result (all_invariants_pass: {inv_data['all_invariants_pass']}):")
            for k, v in inv_data["invariants"].items():
                print(f"         - {k}: {v}")

            # 4. Bookings & CSP Room Alternatives
            print("\n[4/8] Testing GET /api/v1/bookings & GET /api/v1/rooms/alternatives...")
            res_bk = await client.get("/api/v1/bookings", headers=headers)
            assert res_bk.status_code == 200, f"Expected 200, got {res_bk.status_code}: {res_bk.text}"
            bookings = res_bk.json()
            print(f"  [PASS] Retrieved {len(bookings)} active bookings.")
            if bookings:
                exam_bk = bookings[0]
                now = datetime.now(timezone.utc)
                res_alt = await client.get(
                    f"/api/v1/rooms/alternatives?current_room_id={exam_bk['room_node_id']}&student_count=110&start_time={exam_bk['start_time']}&end_time={exam_bk['end_time']}",
                    headers=headers
                )
                assert res_alt.status_code == 200, f"Expected 200, got {res_alt.status_code}: {res_alt.text}"
                alts = res_alt.json()
                print(f"  [PASS] CSP Alternative Solver found {len(alts)} clash-free candidate rooms.")
                if alts:
                    print(f"         Top recommendation: {alts[0]['room_code']} ({alts[0]['room_name']}), Penalty: {alts[0]['penalty_score']}")

            # 5. What-If Dry-Run Simulation
            print("\n[5/8] Testing POST /api/v1/simulations (Dry Run)...")
            sim_req = {
                "scenario_type": "ROOM_UNAVAILABLE",
                "target_node_code": "RM-ACAD-204",
                "description": "Pre-Exam breaker fault test simulation"
            }
            res_sim = await client.post("/api/v1/simulations", json=sim_req, headers=headers)
            assert res_sim.status_code == 201, f"Expected 201, got {res_sim.status_code}: {res_sim.text}"
            sim_data = res_sim.json()
            print(f"  [PASS] Dry-Run Simulation Generated (ID: {sim_data['simulation_id'][:8]}):")
            print(f"         Headline: {sim_data['headline']}")
            print(f"         Consequence Steps: {len(sim_data['consequence_chain'])} causal steps detected.")
            print(f"         Recommended: {sim_data['recommended_plan']} (Disruption: {sim_data['plan_a']['disruption_score']}/100 vs {sim_data['plan_b']['disruption_score']}/100)")

            # 6. Campus 2.5D Map Status
            print("\n[6/8] Testing GET /api/v1/campus/map-status...")
            res_map = await client.get("/api/v1/campus/map-status", headers=headers)
            assert res_map.status_code == 200, f"Expected 200, got {res_map.status_code}: {res_map.text}"
            map_data = res_map.json()
            print(f"  [PASS] 2.5D Campus Map Status for {len(map_data['blocks'])} SRM Easwari Blocks:")
            for b in map_data["blocks"]:
                print(f"         - {b['building_code']} ({b['name'][:30]}): Color={b['color']}, Status={b['status_label']}, ActiveWO={b['active_work_orders']}")

            # 7. React Flow Consequence Graph Data
            print("\n[7/8] Testing GET /api/v1/campus/graph...")
            res_graph = await client.get("/api/v1/campus/graph", headers=headers)
            assert res_graph.status_code == 200, f"Expected 200, got {res_graph.status_code}: {res_graph.text}"
            graph_data = res_graph.json()
            print(f"  [PASS] React Flow Graph: {len(graph_data['nodes'])} nodes, {len(graph_data['edges'])} edges.")

            # 8. Approvals Queue
            print("\n[8/8] Testing GET /api/v1/approvals...")
            res_app = await client.get("/api/v1/approvals", headers=headers)
            assert res_app.status_code == 200, f"Expected 200, got {res_app.status_code}: {res_app.text}"
            approvals = res_app.json()
            print(f"  [PASS] Retrieved {len(approvals)} approval requests.")

        print("\n" + "=" * 80)
        print("ALL 8 ADVANCED MODULE ENDPOINT CHECKS COMPLETED SUCCESSFULLY!")
        print("=" * 80)
    finally:
        await close_db_pool()


if __name__ == "__main__":
    asyncio.run(verify_endpoints())
