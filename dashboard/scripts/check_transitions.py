import asyncio
import asyncpg

async def check():
    conn = await asyncpg.connect('postgresql://postgres:postgres@localhost:5432/campusops')
    rows = await conn.fetch('SELECT from_state, to_state, allowed_roles FROM fsm_state_transitions;')
    for r in rows:
        print(f"{r['from_state']} -> {r['to_state']} ({r['allowed_roles']})")
    await conn.close()

if __name__ == '__main__':
    asyncio.run(check())

