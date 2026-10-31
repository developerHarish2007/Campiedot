import asyncpg
from typing import Optional, AsyncGenerator
from contextlib import asynccontextmanager
from uuid import UUID
from app.config import settings

_db_pool: Optional[asyncpg.Pool] = None


async def init_db_pool() -> asyncpg.Pool:
    global _db_pool
    if _db_pool is None:
        _db_pool = await asyncpg.create_pool(
            host=settings.POSTGRES_HOST,
            port=settings.POSTGRES_PORT,
            user=settings.POSTGRES_USER,
            password=settings.POSTGRES_PASSWORD,
            database=settings.POSTGRES_DB,
            min_size=5,
            max_size=30,
            command_timeout=60,
        )
    return _db_pool


async def close_db_pool() -> None:
    global _db_pool
    if _db_pool is not None:
        await _db_pool.close()
        _db_pool = None


def get_db_pool() -> asyncpg.Pool:
    if _db_pool is None:
        raise RuntimeError("Database connection pool is not initialized.")
    return _db_pool


@asynccontextmanager
async def acquire_db_connection(
    actor_id: Optional[UUID] = None,
    actor_role: Optional[str] = None,
    dept_id: Optional[UUID] = None,
) -> AsyncGenerator[asyncpg.Connection, None]:
    """
    Acquires an asyncpg connection from the pool and establishes the
    secure transaction context (set_secure_context) for role and SoD enforcement.
    """
    pool = get_db_pool()
    async with pool.acquire() as conn:
        if actor_id is not None and actor_role is not None:
            await conn.execute(
                """
                SELECT set_secure_context($1::uuid, $2::user_role, $3::uuid);
                """,
                actor_id,
                actor_role,
                dept_id,
            )
        try:
            yield conn
        finally:
            # Context remains bound to backend_pid and is cleanly overwritten on next acquire
            pass

