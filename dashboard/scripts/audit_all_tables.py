import asyncio
import asyncpg

async def audit_all_tables():
    conn = await asyncpg.connect("postgresql://postgres:postgres@localhost:5432/campusops")
    tables = await conn.fetch("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public' 
        ORDER BY table_name;
    """)
    print("Table row counts:")
    for t in tables:
        tname = t['table_name']
        try:
            cnt = await conn.fetchval(f"SELECT count(*) FROM {tname};")
            print(f"  {tname}: {cnt}")
        except Exception as e:
            print(f"  {tname}: Error - {e}")
    await conn.close()

if __name__ == "__main__":
    asyncio.run(audit_all_tables())
