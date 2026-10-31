import json
import hashlib
from typing import Tuple, Optional, Any, Dict
from datetime import datetime, timezone, timedelta
import asyncpg
from app.core.exceptions import IdempotencyConflictError


def compute_payload_hash(payload: Any) -> str:
    """Computes a deterministic SHA-256 hash of any JSON-serializable payload."""
    canonical_json = json.dumps(payload, sort_keys=True, separators=(',', ':'), default=str)
    return hashlib.sha256(canonical_json.encode('utf-8')).hexdigest()


async def claim_idempotency_key(
    conn: asyncpg.Connection,
    source: str,
    idempotency_key: str,
    payload: Any,
    worker_id: str = "fastapi-worker",
    lease_seconds: int = 30
) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """
    Attempts to atomically claim an idempotency key in processed_events.
    Handles high-concurrency race conditions via ON CONFLICT DO NOTHING.
    Returns:
        (is_new_claim, cached_response)
        - If (True, None): The caller owns the lease and MUST execute the transaction.
        - If (False, cached_response): Duplicate call; return cached_response immediately.
    Raises:
        IdempotencyConflictError if payload hash does not match stored hash.
    """
    payload_hash = compute_payload_hash(payload)
    now = datetime.now(timezone.utc)
    lease_expires_at = now + timedelta(seconds=lease_seconds)

    # 1. Attempt atomic insert with ON CONFLICT DO NOTHING
    try:
        inserted = await conn.fetchval(
            """
            INSERT INTO processed_events (
                source, idempotency_key, payload_hash, status, worker_id,
                attempt_count, claimed_at, lease_expires_at
            )
            VALUES ($1, $2, $3, 'PROCESSING', $4, 1, $5, $6)
            ON CONFLICT (source, idempotency_key) DO NOTHING
            RETURNING 1;
            """,
            source,
            idempotency_key,
            payload_hash,
            worker_id,
            now,
            lease_expires_at
        )
        if inserted:
            return True, None
    except asyncpg.exceptions.UniqueViolationError:
        pass

    # 2. Row exists or was inserted concurrently: Lock and evaluate state
    row = await conn.fetchrow(
        """
        SELECT status, payload_hash, response_status, response_payload, lease_expires_at
        FROM processed_events
        WHERE source = $1 AND idempotency_key = $2
        FOR UPDATE;
        """,
        source,
        idempotency_key
    )

    if not row:
        return True, None

    # Check payload tamper
    if row["payload_hash"] != payload_hash:
        raise IdempotencyConflictError(
            key=idempotency_key,
            reason="Payload hash does not match previously recorded payload for this idempotency key."
        )

    # Row is completed: return cached payload
    if row["status"] == "COMPLETED":
        return False, {
            "cached": True,
            "status_code": row["response_status"],
            "data": row["response_payload"]
        }

    # Row is in PROCESSING: check lease expiry
    lease_expires = row["lease_expires_at"]
    if lease_expires and lease_expires < now:
        # Lease expired! Reclaim work
        await conn.execute(
            """
            UPDATE processed_events
            SET status = 'PROCESSING',
                worker_id = $3,
                attempt_count = attempt_count + 1,
                claimed_at = $4,
                lease_expires_at = $5
            WHERE source = $1 AND idempotency_key = $2;
            """,
            source,
            idempotency_key,
            worker_id,
            now,
            lease_expires_at
        )
        return True, None

    # Lease is currently active by another worker
    return False, {
        "cached": True,
        "status_code": 202,
        "data": {"status": "IN_PROGRESS", "message": "Event is currently being processed by another worker"}
    }


async def complete_idempotency_key(
    conn: asyncpg.Connection,
    source: str,
    idempotency_key: str,
    response_status: int,
    response_payload: Any
) -> None:
    """Marks an idempotency key as COMPLETED and records the authoritative response."""
    await conn.execute(
        """
        UPDATE processed_events
        SET status = 'COMPLETED',
            response_status = $3,
            response_payload = $4::jsonb
        WHERE source = $1 AND idempotency_key = $2;
        """,
        source,
        idempotency_key,
        response_status,
        json.dumps(response_payload, default=str)
    )
