import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional
import asyncpg
from app.database import get_db_pool

logger = logging.getLogger("outbox_worker")


async def process_outbox_batch(conn: asyncpg.Connection, simulate_failure_ids: Optional[list] = None) -> int:
    """
    Processes a single batch of up to 10 pending outbound notifications.
    Uses 'FOR UPDATE SKIP LOCKED' to prevent duplicate delivery across parallel workers.
    """
    simulate_failure_ids = simulate_failure_ids or []
    processed_count = 0

    async with conn.transaction():
        rows = await conn.fetch(
            """
            SELECT id, recipient_email, channel, subject, body, attempt_count
            FROM outbound_notifications
            WHERE delivery_status = 'PENDING' 
              AND next_retry_at <= NOW()
            LIMIT 10
            FOR UPDATE SKIP LOCKED;
            """
        )

        for row in rows:
            notif_id = row["id"]
            attempts = row["attempt_count"] + 1

            if notif_id in simulate_failure_ids:
                # Simulated delivery failure
                if attempts >= 5:
                    await conn.execute(
                        """
                        UPDATE outbound_notifications
                        SET delivery_status = 'DEAD_LETTER',
                            attempt_count = $2
                        WHERE id = $1;
                        """,
                        notif_id,
                        attempts
                    )
                else:
                    delay_seconds = 2 ** attempts
                    await conn.execute(
                        """
                        UPDATE outbound_notifications
                        SET attempt_count = $2,
                            next_retry_at = NOW() + ($3 || ' seconds')::interval
                        WHERE id = $1;
                        """,
                        notif_id,
                        attempts,
                        str(delay_seconds)
                    )
            else:
                # Successful delivery
                logger.info(f"Delivered notification {notif_id} to {row['recipient_email']}: {row['subject']}")
                await conn.execute(
                    """
                    UPDATE outbound_notifications
                    SET delivery_status = 'DELIVERED',
                        attempt_count = $2
                    WHERE id = $1;
                    """,
                    notif_id,
                    attempts
                )
            processed_count += 1

    return processed_count


async def run_outbox_loop(poll_interval: int = 3, stop_event: Optional[asyncio.Event] = None):
    """Continuous background worker loop for outbox notification dispatch."""
    logger.info("Outbox worker started.")
    while not (stop_event and stop_event.is_set()):
        try:
            pool = get_db_pool()
            async with pool.acquire() as conn:
                count = await process_outbox_batch(conn)
                if count > 0:
                    logger.debug(f"Outbox worker processed {count} notification(s).")
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Error in outbox worker loop: {e}", exc_info=True)

        try:
            await asyncio.sleep(poll_interval)
        except asyncio.CancelledError:
            break
    logger.info("Outbox worker stopped.")

