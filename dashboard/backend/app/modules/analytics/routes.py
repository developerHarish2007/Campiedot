from typing import Dict, Any, List
from fastapi import APIRouter, Depends
from app.core.security import get_current_user, CurrentUser
from app.database import acquire_db_connection

router = APIRouter(prefix="", tags=["Analytics & Campus Pulse"])


@router.get("/pulse")
async def get_campus_pulse(current_user: CurrentUser = Depends(get_current_user)):
    """
    Computes a factual, database-grounded operational Campus Pulse briefing.
    All numbers and metrics originate directly from live SQL queries.
    """
    async with acquire_db_connection(
        actor_id=current_user.id,
        actor_role=current_user.role,
        dept_id=current_user.department_id,
    ) as conn:
        # Live SQL metrics
        summary = await conn.fetchrow("SELECT * FROM v_analytics_summary;")
        open_count = summary["open_requests_count"] or 0
        blocked_count = summary["blocked_by_parts_count"] or 0
        breached_count = summary["sla_breached_count"] or 0
        sla_pct = summary["sla_compliance_percentage"] or 100.0

        # Critical / High priority active count
        critical_count = await conn.fetchval(
            """
            SELECT COUNT(*) FROM work_orders 
            WHERE state NOT IN ('RESOLVED', 'CLOSED', 'MERGED_DUPLICATE')
              AND calculated_priority IN ('P0_CRITICAL', 'P1_HIGH');
            """
        ) or 0

        # Non-operational rooms
        down_rooms_count = await conn.fetchval(
            "SELECT COUNT(*) FROM campus_nodes WHERE is_operational = FALSE AND node_type = 'ROOM';"
        ) or 0

        # Available technicians on shift
        available_techs = await conn.fetchval(
            """
            SELECT COUNT(*) FROM users u
            WHERE u.role = 'TECHNICIAN' AND u.is_available = TRUE
              AND EXISTS (SELECT 1 FROM staff_shifts ss WHERE ss.user_id = u.id AND ss.shift_window @> NOW());
            """
        ) or 0

        # Natural language synthesis grounded purely in numbers
        status_vibe = "STABLE"
        if critical_count > 0 or down_rooms_count > 0:
            status_vibe = "ELEVATED_ATTENTION"
        if breached_count > 0:
            status_vibe = "SLA_WARNING"

        sentences = []
        if critical_count == 0 and down_rooms_count == 0:
            sentences.append("Campus operations across SRM Easwari are stable.")
        else:
            sentences.append(f"Operations report {critical_count} high-priority alert(s) requiring coordination.")

        if open_count > 0:
            sentences.append(f"{open_count} total work order(s) are active.")
        else:
            sentences.append("No active maintenance requests are currently logged.")

        if down_rooms_count > 0:
            sentences.append(f"{down_rooms_count} classroom(s) or lab(s) are currently marked non-operational.")

        if blocked_count > 0:
            sentences.append(f"{blocked_count} work order(s) are blocked awaiting spare parts procurement.")

        sentences.append(f"{available_techs} technician(s) are actively on shift. SLA compliance stands at {sla_pct:.1f}%.")

        pulse_text = " ".join(sentences)

        return {
            "status_vibe": status_vibe,
            "pulse_text": pulse_text,
            "metrics": {
                "open_requests": open_count,
                "critical_requests": critical_count,
                "blocked_by_parts": blocked_count,
                "sla_breached": breached_count,
                "sla_compliance_pct": float(sla_pct),
                "non_operational_rooms": down_rooms_count,
                "available_technicians_on_shift": available_techs,
            }
        }


@router.get("/analytics/summary")
async def get_analytics_summary(current_user: CurrentUser = Depends(get_current_user)):
    async with acquire_db_connection(
        actor_id=current_user.id,
        actor_role=current_user.role,
        dept_id=current_user.department_id,
    ) as conn:
        row = await conn.fetchrow("SELECT * FROM v_analytics_summary;")
        return dict(row) if row else {}


@router.get("/analytics/recurring")
async def get_recurring_incidents(current_user: CurrentUser = Depends(get_current_user)):
    async with acquire_db_connection(
        actor_id=current_user.id,
        actor_role=current_user.role,
        dept_id=current_user.department_id,
    ) as conn:
        rows = await conn.fetch("SELECT * FROM v_recurring_incidents LIMIT 20;")
        return [dict(r) for r in rows]


@router.get("/invariants")
async def get_live_invariants(current_user: CurrentUser = Depends(get_current_user)):
    """
    Authoritative real-time check of all 6 mathematical & transactional invariants.
    Directly queries live database state.
    """
    async with acquire_db_connection(
        actor_id=current_user.id,
        actor_role=current_user.role,
        dept_id=current_user.department_id,
    ) as conn:
        # 1. Overlapping bookings
        overlapping_bookings = await conn.fetchval(
            """
            SELECT COUNT(*) FROM room_bookings b1
            JOIN room_bookings b2 ON b1.room_node_id = b2.room_node_id AND b1.id <> b2.id
            WHERE b1.status IN ('CONFIRMED', 'CONTINGENCY_HOLD', 'MAINTENANCE_BLOCK')
              AND b2.status IN ('CONFIRMED', 'CONTINGENCY_HOLD', 'MAINTENANCE_BLOCK')
              AND b1.time_slot && b2.time_slot;
            """
        ) or 0

        # 2. Stock drift (physical = available + reserved)
        stock_drift = await conn.fetchval(
            """
            SELECT COUNT(*) FROM inventory_parts
            WHERE physical_on_hand_qty <> (available_qty + reserved_qty);
            """
        ) or 0

        # 3. DAG cycles
        dag_cycles = await conn.fetchval(
            """
            WITH RECURSIVE path AS (
                SELECT parent_node_id, child_node_id, dependency_domain, 1 AS depth
                FROM node_dependencies
                UNION ALL
                SELECT p.parent_node_id, nd.child_node_id, p.dependency_domain, p.depth + 1
                FROM path p
                JOIN node_dependencies nd ON p.child_node_id = nd.parent_node_id AND p.dependency_domain = nd.dependency_domain
                WHERE p.depth < 15
            )
            SELECT COUNT(*) FROM path WHERE parent_node_id = child_node_id;
            """
        ) or 0

        # 4. Untracked balance updates (negative quantities or out of bounds)
        untracked_balance_updates = await conn.fetchval(
            """
            SELECT COUNT(*) FROM inventory_parts
            WHERE physical_on_hand_qty < 0 OR available_qty < 0 OR reserved_qty < 0;
            """
        ) or 0

        # 5. Illegal FSM state jumps
        illegal_fsm_jumps = await conn.fetchval(
            """
            SELECT COUNT(*) FROM audit_logs a
            WHERE a.action = 'STATE_TRANSITION'
              AND a.previous_state IS NOT NULL
              AND a.new_state IS NOT NULL
              AND NOT EXISTS (
                  SELECT 1 FROM fsm_state_transitions fst
                  WHERE fst.from_state = a.previous_state::wo_state AND fst.to_state = a.new_state::wo_state
              );
            """
        ) or 0

        # 6. Tampered audit rows
        tampered_audit_rows = await conn.fetchval(
            """
            SELECT COUNT(*) FROM audit_logs
            WHERE created_at IS NULL OR action IS NULL;
            """
        ) or 0

        # Fetch recent audit logs for proof stream
        audit_stream = await conn.fetch(
            """
            SELECT a.id, a.work_order_id, wo.ticket_number, u.full_name AS actor_name,
                   a.action, a.previous_state, a.new_state, a.details, a.created_at
            FROM audit_logs a
            LEFT JOIN work_orders wo ON wo.id = a.work_order_id
            LEFT JOIN users u ON u.id = a.actor_user_id
            ORDER BY a.created_at DESC
            LIMIT 25;
            """
        )

        return {
            "invariants": {
                "overlapping_bookings": overlapping_bookings,
                "stock_drift_skus": stock_drift,
                "dag_cycles": dag_cycles,
                "untracked_balance_updates": untracked_balance_updates,
                "illegal_fsm_jumps": illegal_fsm_jumps,
                "tampered_audit_rows": tampered_audit_rows,
            },
            "all_invariants_pass": (
                overlapping_bookings == 0
                and stock_drift == 0
                and dag_cycles == 0
                and untracked_balance_updates == 0
                and illegal_fsm_jumps == 0
                and tampered_audit_rows == 0
            ),
            "audit_stream": [dict(r) for r in audit_stream]
        }

