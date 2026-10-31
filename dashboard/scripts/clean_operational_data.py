#!/usr/bin/env python3
"""
CampusOps: Operational Data Cleaner
Wipes simulated work orders, mock bookings, pending approvals, and test events.
Preserves campus infrastructure, departments, users, and inventory master catalogs.
"""

import asyncio
import os
import asyncpg
from dotenv import load_dotenv

load_dotenv()

DB_HOST = os.getenv("POSTGRES_HOST", "localhost")
DB_PORT = int(os.getenv("POSTGRES_PORT", 5432))
DB_USER = os.getenv("POSTGRES_USER", "postgres")
DB_PASS = os.getenv("POSTGRES_PASSWORD", "postgres")
DB_NAME = os.getenv("POSTGRES_DB", "campusops")


async def clean_simulated_data():
    print("=" * 70)
    print("CAMPUSOPS: REMOVING ALL SIMULATED OPERATIONAL DATA")
    print(f"Connecting to postgresql://{DB_USER}:****@{DB_HOST}:{DB_PORT}/{DB_NAME}")
    print("=" * 70)

    conn = await asyncpg.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASS,
        database=DB_NAME,
    )

    try:
        # 1. Clean child transactional tables
        print("\n[1/6] Deleting notifications, outbox events, and idempotency records...")
        await conn.execute("DELETE FROM outbound_notifications;")
        await conn.execute("DELETE FROM processed_events;")

        # 2. Clean approvals, part reservations, and bookings
        print("[2/6] Deleting simulated approvals, reservations, and bookings...")
        await conn.execute("DELETE FROM approvals;")
        await conn.execute("DELETE FROM part_reservations;")
        await conn.execute("DELETE FROM room_bookings;")

        # 3. Clean audit logs by temporarily disabling immutability trigger
        print("[3/6] Purging simulated audit logs...")
        await conn.execute("ALTER TABLE audit_logs DISABLE TRIGGER trg_audit_tamper_guard_row;")
        await conn.execute("ALTER TABLE audit_logs DISABLE TRIGGER trg_audit_tamper_guard_stmt;")
        await conn.execute("DELETE FROM audit_logs;")
        await conn.execute("ALTER TABLE audit_logs ENABLE TRIGGER trg_audit_tamper_guard_row;")
        await conn.execute("ALTER TABLE audit_logs ENABLE TRIGGER trg_audit_tamper_guard_stmt;")

        # 4. Clean work orders
        print("[4/6] Deleting all simulated work orders...")
        await conn.execute("UPDATE work_orders SET parent_master_wo_id = NULL;")
        await conn.execute("DELETE FROM work_orders;")

        # 5. Reset inventory stock to baseline physical reality with zero reserved
        print("[5/6] Resetting inventory 3-bucket stock (reserved_qty = 0)...")
        await conn.execute("ALTER TABLE inventory_parts DISABLE TRIGGER trg_inventory_tamper_guard;")
        await conn.execute(
            """
            UPDATE inventory_parts
            SET reserved_qty = 0,
                available_qty = physical_on_hand_qty;
            """
        )
        await conn.execute("ALTER TABLE inventory_parts ENABLE TRIGGER trg_inventory_tamper_guard;")

        # 6. Reset staff workload counters
        print("[6/6] Resetting technician active workload counters to 0...")
        await conn.execute("UPDATE users SET active_workload_count = 0;")

        # Verification check
        wo_count = await conn.fetchval("SELECT COUNT(*) FROM work_orders;")
        app_count = await conn.fetchval("SELECT COUNT(*) FROM approvals;")
        bkg_count = await conn.fetchval("SELECT COUNT(*) FROM room_bookings;")
        audit_count = await conn.fetchval("SELECT COUNT(*) FROM audit_logs;")

        print("\n" + "=" * 70)
        print("SIMULATED DATA PURGE COMPLETE - CLEAN SYSTEM STATE VERIFIED:")
        print(f"  - Active Work Orders:  {wo_count}")
        print(f"  - Pending Approvals:   {app_count}")
        print(f"  - Active Bookings:     {bkg_count}")
        print(f"  - Audit Log Rows:      {audit_count}")
        print("=" * 70)

    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(clean_simulated_data())
