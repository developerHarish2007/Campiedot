#!/usr/bin/env python3
"""
CampusOps: Database Setup & Migration Script
Connects to PostgreSQL, recreates the 'campusops' database cleanly,
and executes backend/migrations/init.sql.
"""

import asyncio
import os
import sys
import asyncpg
from dotenv import load_dotenv

load_dotenv()

DB_HOST = os.getenv("POSTGRES_HOST", "localhost")
DB_PORT = int(os.getenv("POSTGRES_PORT", 5432))
DB_USER = os.getenv("POSTGRES_USER", "postgres")
DB_PASS = os.getenv("POSTGRES_PASSWORD", "postgres")
DB_NAME = os.getenv("POSTGRES_DB", "campusops")


async def setup_database():
    print(f"Connecting to postgres server at {DB_HOST}:{DB_PORT} as {DB_USER}...")
    try:
        # Connect to default maintenance database 'postgres'
        conn = await asyncpg.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASS,
            database="postgres",
        )
    except Exception as e:
        print(f"[ERROR] Could not connect to default 'postgres' database: {e}")
        return False

    try:
        # Terminate any active connections to campusops
        print(f"Terminating any active connections to '{DB_NAME}'...")
        await conn.execute(
            f"""
            SELECT pg_terminate_backend(pid) 
            FROM pg_stat_activity 
            WHERE datname = '{DB_NAME}' AND pid <> pg_backend_pid();
            """
        )

        # Drop and recreate campusops database for a clean state
        print(f"Recreating database '{DB_NAME}'...")
        await conn.execute(f'DROP DATABASE IF EXISTS "{DB_NAME}";')
        await conn.execute(f'CREATE DATABASE "{DB_NAME}";')
        print(f"Database '{DB_NAME}' created cleanly.")
    finally:
        await conn.close()

    # Connect to 'campusops' database and apply init.sql
    print(f"Connecting to '{DB_NAME}' to apply migrations/init.sql...")
    conn = await asyncpg.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASS,
        database=DB_NAME,
    )

    try:
        migration_path = os.path.join(
            os.path.dirname(__file__), "..", "backend", "migrations", "init.sql"
        )
        with open(migration_path, "r", encoding="utf-8") as f:
            sql_script = f.read()

        print("Executing init.sql DDL script...")
        await conn.execute(sql_script)
        print("Schema, tables, functions, triggers, and views initialized successfully!")
        return True
    except Exception as e:
        print(f"[ERROR] Failed applying init.sql: {e}")
        return False
    finally:
        await conn.close()


if __name__ == "__main__":
    success = asyncio.run(setup_database())
    sys.exit(0 if success else 1)
