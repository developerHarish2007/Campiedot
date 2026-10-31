import asyncio
import asyncpg

async def migrate():
    conn = await asyncpg.connect('postgresql://postgres:postgres@localhost:5432/campusops')
    await conn.execute("""
        INSERT INTO fsm_state_transitions (from_state, to_state, allowed_roles)
        VALUES 
            ('INGESTED', 'ASSIGNED', ARRAY['SYS_ADMIN'::user_role, 'FACILITIES_ADMIN'::user_role, 'DEPT_MANAGER'::user_role]),
            ('AWAITING_CLARIFICATION', 'ASSIGNED', ARRAY['SYS_ADMIN'::user_role, 'FACILITIES_ADMIN'::user_role, 'DEPT_MANAGER'::user_role])
        ON CONFLICT DO NOTHING;
    """)
    print('FSM updated: INGESTED -> ASSIGNED allowed.')
    await conn.close()

if __name__ == '__main__':
    asyncio.run(migrate())
