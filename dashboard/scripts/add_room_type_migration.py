import asyncio
import asyncpg

async def migrate():
    conn = await asyncpg.connect("postgresql://postgres:postgres@localhost:5432/campusops")
    await conn.execute("ALTER TABLE campus_nodes ADD COLUMN IF NOT EXISTS room_type VARCHAR(32) DEFAULT 'CLASSROOM';")
    await conn.execute("UPDATE campus_nodes SET room_type = 'LAB' WHERE node_code LIKE 'LAB-%' OR name ILIKE '%lab%';")
    await conn.execute("UPDATE campus_nodes SET room_type = 'AUDITORIUM' WHERE node_code LIKE 'RM-AUD-%' OR name ILIKE '%auditorium%' OR name ILIKE '%amphitheatre%';")
    await conn.execute("UPDATE campus_nodes SET room_type = 'SEMINAR_HALL' WHERE name ILIKE '%seminar%' OR name ILIKE '%boardroom%';")
    await conn.execute("UPDATE campus_nodes SET room_type = 'WORKSHOP' WHERE name ILIKE '%workshop%';")
    print("Migrated room_type column successfully.")
    await conn.close()

if __name__ == "__main__":
    asyncio.run(migrate())

