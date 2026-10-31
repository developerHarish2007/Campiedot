import asyncio
import asyncpg

async def clean_workers():
    conn = await asyncpg.connect("postgresql://postgres:postgres@localhost:5432/campusops")
    print("Cleaning simulated technicians from database...")
    
    # Check current technicians
    techs = await conn.fetch("SELECT id, full_name, email FROM users WHERE role = 'TECHNICIAN';")
    print(f"Found {len(techs)} technicians:")
    for t in techs:
        print(f"  - {t['full_name']} ({t['email']})")
        
    # Unassign work orders first if they reference technicians
    await conn.execute("UPDATE work_orders SET assigned_tech_id = NULL WHERE assigned_tech_id IS NOT NULL;")
    
    # Delete staff_skills and staff_shifts for technicians
    await conn.execute("""
        DELETE FROM staff_skills WHERE user_id IN (
            SELECT id FROM users WHERE role = 'TECHNICIAN'
        );
    """)
    await conn.execute("""
        DELETE FROM staff_shifts WHERE user_id IN (
            SELECT id FROM users WHERE role = 'TECHNICIAN'
        );
    """)
    
    # Clear references in outbound_notifications and audit_logs
    await conn.execute("""
        UPDATE outbound_notifications SET recipient_user_id = NULL WHERE recipient_user_id IN (
            SELECT id FROM users WHERE role = 'TECHNICIAN'
        );
    """)
    await conn.execute("""
        UPDATE audit_logs SET actor_user_id = NULL WHERE actor_user_id IN (
            SELECT id FROM users WHERE role = 'TECHNICIAN'
        );
    """)
    
    # Delete technician users
    deleted = await conn.execute("DELETE FROM users WHERE role = 'TECHNICIAN';")
    print(f"Deleted simulated technicians: {deleted}")
    
    # Check remaining users
    users = await conn.fetch("SELECT id, full_name, email, role FROM users;")
    print(f"\nRemaining users in DB ({len(users)}):")
    for u in users:
        print(f"  {u['id']}: {u['full_name']} ({u['email']}) - Role: {u['role']}")
        
    await conn.close()

if __name__ == "__main__":
    asyncio.run(clean_workers())
