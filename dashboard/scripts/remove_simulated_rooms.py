import asyncio
import asyncpg

async def remove_simulated_rooms():
    conn = await asyncpg.connect("postgresql://postgres:postgres@localhost:5432/campusops")
    # 1. Delete node dependencies that reference rooms
    await conn.execute("""
        DELETE FROM node_dependencies 
        WHERE parent_node_id IN (SELECT id FROM campus_nodes WHERE node_type = 'ROOM')
           OR child_node_id IN (SELECT id FROM campus_nodes WHERE node_type = 'ROOM');
    """)
    # 2. Delete all simulated rooms
    deleted = await conn.execute("DELETE FROM campus_nodes WHERE node_type = 'ROOM';")
    print(f"Removed simulated rooms: {deleted}")
    
    remaining = await conn.fetchval("SELECT COUNT(*) FROM campus_nodes WHERE node_type = 'ROOM';")
    print(f"Remaining registered rooms: {remaining}")
    await conn.close()

if __name__ == "__main__":
    asyncio.run(remove_simulated_rooms())

