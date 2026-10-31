import asyncio
import asyncpg

async def check():
    conn = await asyncpg.connect("postgresql://postgres:postgres@localhost:5432/campusops")
    tables = [
        'work_orders', 'audit_logs', 'outbound_notifications',
        'approvals', 'inventory_parts', 'room_bookings',
        'campus_nodes', 'node_dependencies', 'staff_skills', 'staff_shifts', 'users'
    ]
    for t in tables:
        c = await conn.fetchval(f"SELECT count(*) FROM {t}")
        print(f"{t}: {c}")

    nodes = await conn.fetch("SELECT node_code, name, node_type FROM campus_nodes;")
    print("\nCampus Nodes:")
    for n in nodes:
        print(f"  {n['node_code']} ({n['name']}) - {n['node_type']}")

    wos = await conn.fetch("SELECT ticket_number, state, raw_description FROM work_orders;")
    print("\nWork Orders:")
    for w in wos:
        print(f"  #{w['ticket_number']}: {w['state']} - {w['raw_description'][:50] if w['raw_description'] else 'None'}")

    await conn.close()

if __name__ == "__main__":
    asyncio.run(check())

