import asyncio
import asyncpg

async def remove_simulated_inventory():
    conn = await asyncpg.connect("postgresql://postgres:postgres@localhost:5432/campusops")
    # 1. Delete part reservations and inventory movements
    await conn.execute("DELETE FROM part_reservations;")
    await conn.execute("DELETE FROM inventory_movements;")
    # 2. Delete inventory parts
    deleted = await conn.execute("DELETE FROM inventory_parts;")
    print(f"Removed simulated inventory: {deleted}")
    
    remaining = await conn.fetchval("SELECT COUNT(*) FROM inventory_parts;")
    print(f"Remaining inventory parts: {remaining}")
    await conn.close()

if __name__ == "__main__":
    asyncio.run(remove_simulated_inventory())

