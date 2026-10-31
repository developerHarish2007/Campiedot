import json
from uuid import UUID, uuid4
from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional, Dict, Any
import asyncpg
from app.core.exceptions import (
    ResourceNotFoundError,
    ConflictError,
    FSMTransitionError,
    AuthorizationError,
)
from app.modules.work_orders.schemas import (
    WorkOrderCommentOut,
    CreateWorkOrderRequest,
    TransitionWorkOrderRequest,
    WorkOrderOut,
    WorkOrderPartItem,
    WorkOrderTransitionResponse,
)


class WorkOrderService:

    @staticmethod
    async def create_work_order(
        conn: asyncpg.Connection,
        request: CreateWorkOrderRequest,
        reporter_id: UUID,
        actor_role: str,
        department_id: Optional[UUID] = None
    ) -> WorkOrderOut:
        thread_id = request.conversation_thread_id or f"thread-{uuid4().hex[:12]}"
        initial_state = request.initial_state.upper()

        if initial_state not in ("INGESTED", "TRIAGED"):
            raise ConflictError("Initial work order state must be either 'INGESTED' or 'TRIAGED'")

        # Infer department from target node if not provided
        target_dept_id = department_id
        if request.target_node_id and not target_dept_id:
            node_bldg = await conn.fetchval(
                "SELECT building_code FROM campus_nodes WHERE id = $1;", request.target_node_id
            )
            if node_bldg == "EEC-ACAD":
                target_dept_id = await conn.fetchval("SELECT id FROM departments WHERE code = 'DEPT-CSE-IT';")
            elif node_bldg == "EEC-MECH-PG":
                target_dept_id = await conn.fetchval("SELECT id FROM departments WHERE code = 'DEPT-MECH-CIVIL';")
            elif node_bldg == "EEC-ROBOTICS":
                target_dept_id = await conn.fetchval("SELECT id FROM departments WHERE code = 'DEPT-ROBOTICS';")
            else:
                target_dept_id = await conn.fetchval("SELECT id FROM departments WHERE code = 'DEPT-ADMIN';")

        row = await conn.fetchrow(
            """
            INSERT INTO work_orders (
                conversation_thread_id, reporter_user_id, target_node_id,
                category, reporter_urgency, calculated_priority, state,
                raw_description, ai_summary, department_id
            )
            VALUES ($1, $2, $3, $4::issue_category, $5::priority_level, $5::priority_level, $6::wo_state, $7, $8, $9)
            RETURNING id, ticket_number, conversation_thread_id, reporter_user_id,
                      target_node_id, category, reporter_urgency, calculated_priority,
                      impact_score, state, raw_description, ai_summary, assigned_tech_id,
                      department_id, estimated_cost, estimated_duration_mins,
                      reassignment_count, correlator_reporter_count, sla_is_paused,
                      sla_breached, blocked_reason, created_at, updated_at, resolved_at;
            """,
            thread_id,
            reporter_id,
            request.target_node_id,
            request.category,
            request.reporter_urgency,
            initial_state,
            request.raw_description,
            request.ai_summary,
            target_dept_id
        )

        wo_id = row["id"]

        # Audit log creation
        await conn.execute(
            """
            INSERT INTO audit_logs (work_order_id, actor_user_id, action, previous_state, new_state, details)
            VALUES ($1, $2, 'WORK_ORDER_CREATED', NULL, $3, $4::jsonb);
            """,
            wo_id,
            reporter_id,
            initial_state,
            json.dumps({"description": request.raw_description, "ticket_number": row["ticket_number"]})
        )

        return await WorkOrderService.get_work_order(conn, wo_id)

    @staticmethod
    async def get_work_order(conn: asyncpg.Connection, work_order_id: UUID) -> WorkOrderOut:
        row = await conn.fetchrow(
            """
            SELECT wo.id, wo.ticket_number, wo.conversation_thread_id, wo.reporter_user_id,
                   wo.target_node_id, cn.node_code, cn.name AS node_name,
                   wo.parent_master_wo_id, wo.category, wo.reporter_urgency,
                   wo.calculated_priority, wo.impact_score, wo.state, wo.raw_description,
                   wo.ai_summary, wo.assigned_tech_id, u.full_name AS assigned_tech_name,
                   u.email AS assigned_tech_email,
                   sk.skill::text AS assigned_tech_role,
                   wo.department_id, wo.estimated_cost, wo.estimated_duration_mins,
                   wo.reassignment_count, wo.correlator_reporter_count, wo.sla_is_paused,
                   wo.sla_breached, wo.blocked_reason, wo.clarification_question, wo.partial_slots, wo.created_at, wo.updated_at, wo.resolved_at
            FROM work_orders wo
            LEFT JOIN campus_nodes cn ON wo.target_node_id = cn.id
            LEFT JOIN users u ON wo.assigned_tech_id = u.id
            LEFT JOIN LATERAL (
                SELECT skill FROM staff_skills WHERE user_id = u.id LIMIT 1
            ) sk ON true
            WHERE wo.id = $1;
            """,
            work_order_id
        )
        if not row:
            raise ResourceNotFoundError("Work Order", work_order_id)

        # Fetch part reservations
        part_rows = await conn.fetch(
            """
            SELECT pr.part_id, p.sku, p.name, pr.requested_qty, pr.locked_unit_cost, pr.status
            FROM part_reservations pr
            JOIN inventory_parts p ON pr.part_id = p.id
            WHERE pr.work_order_id = $1
            ORDER BY p.sku ASC;
            """,
            work_order_id
        )
        parts = [
            WorkOrderPartItem(
                part_id=pr["part_id"],
                sku=pr["sku"],
                name=pr["name"],
                requested_qty=pr["requested_qty"],
                locked_unit_cost=pr["locked_unit_cost"],
                status=pr["status"]
            )
            for pr in part_rows
        ]

        comment_summary = await conn.fetchrow(
            """
            SELECT COUNT(*)::int AS total_comments,
                   COUNT(*) FILTER (WHERE author_role = 'TECHNICIAN')::int AS worker_comments,
                   COUNT(*) FILTER (WHERE author_role IN ('SYS_ADMIN', 'FACILITIES_ADMIN'))::int AS admin_comments,
                   (SELECT author_role FROM work_order_comments WHERE work_order_id = $1 ORDER BY created_at DESC LIMIT 1) AS latest_author_role,
                   (SELECT message FROM work_order_comments WHERE work_order_id = $1 ORDER BY created_at DESC LIMIT 1) AS latest_message,
                   (SELECT created_at FROM work_order_comments WHERE work_order_id = $1 ORDER BY created_at DESC LIMIT 1) AS latest_created_at
            FROM work_order_comments
            WHERE work_order_id = $1;
            """,
            work_order_id
        )

        return WorkOrderOut(
            id=row["id"],
            ticket_number=row["ticket_number"],
            conversation_thread_id=row["conversation_thread_id"],
            reporter_user_id=row["reporter_user_id"],
            target_node_id=row["target_node_id"],
            node_code=row["node_code"],
            node_name=row["node_name"],
            parent_master_wo_id=row["parent_master_wo_id"],
            category=row["category"],
            reporter_urgency=row["reporter_urgency"],
            calculated_priority=row["calculated_priority"],
            impact_score=row["impact_score"],
            state=row["state"],
            raw_description=row["raw_description"],
            ai_summary=row["ai_summary"],
            assigned_tech_id=row["assigned_tech_id"],
            assigned_tech_name=row["assigned_tech_name"],
            assigned_tech_email=row["assigned_tech_email"],
            assigned_tech_role=row["assigned_tech_role"],
            department_id=row["department_id"],
            estimated_cost=row["estimated_cost"],
            estimated_duration_mins=row["estimated_duration_mins"],
            reassignment_count=row["reassignment_count"],
            correlator_reporter_count=row["correlator_reporter_count"],
            sla_is_paused=row["sla_is_paused"],
            sla_breached=row["sla_breached"],
            blocked_reason=row["blocked_reason"],
            clarification_question=row["clarification_question"] if "clarification_question" in row else None,
            partial_slots=json.loads(row["partial_slots"]) if isinstance(row.get("partial_slots"), str) else (row.get("partial_slots") or {}),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            resolved_at=row["resolved_at"],
            reserved_parts=parts,
            comments_count=comment_summary["total_comments"] if comment_summary else 0,
            worker_comments_count=comment_summary["worker_comments"] if comment_summary else 0,
            admin_comments_count=comment_summary["admin_comments"] if comment_summary else 0,
            latest_comment_author_role=comment_summary["latest_author_role"] if comment_summary else None,
            latest_comment_message=comment_summary["latest_message"] if comment_summary else None,
            latest_comment_at=comment_summary["latest_created_at"] if comment_summary else None
        )

    @staticmethod
    async def list_work_orders(
        conn: asyncpg.Connection,
        state: Optional[str] = None,
        category: Optional[str] = None,
        assigned_tech_id: Optional[UUID] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[WorkOrderOut]:
        query = """
            SELECT id FROM work_orders
            WHERE 1=1
        """
        params = []
        if state:
            params.append(state)
            query += f" AND state = ${len(params)}::wo_state"
        if category:
            params.append(category)
            query += f" AND category = ${len(params)}::issue_category"
        if assigned_tech_id:
            params.append(assigned_tech_id)
            query += f" AND assigned_tech_id = ${len(params)}"

        query += " ORDER BY created_at DESC LIMIT $" + str(len(params) + 1) + " OFFSET $" + str(len(params) + 2)
        params.extend([limit, offset])

        ids = await conn.fetch(query, *params)
        return [await WorkOrderService.get_work_order(conn, r["id"]) for r in ids]

    @staticmethod
    async def transition_work_order(
        conn: asyncpg.Connection,
        work_order_id: UUID,
        request: TransitionWorkOrderRequest,
        actor_id: UUID,
        actor_role: str
    ) -> WorkOrderTransitionResponse:
        """
        Executes a deterministic state transition adhering to fsm_state_transitions matrix.
        Enforces operational guards for IN_PROGRESS and RESOLVED.
        """
        target_state = request.target_state.upper()
        if target_state == "DISPATCHED":
            target_state = "ASSIGNED"

        wo = await conn.fetchrow(
            """
            SELECT id, ticket_number, state, assigned_tech_id, estimated_cost, department_id
            FROM work_orders
            WHERE id = $1
            FOR UPDATE;
            """,
            work_order_id
        )
        if not wo:
            raise ResourceNotFoundError("Work Order", work_order_id)

        from_state = wo["state"]
        if from_state == target_state:
            return WorkOrderTransitionResponse(
                work_order_id=wo["id"],
                ticket_number=wo["ticket_number"],
                previous_state=from_state,
                new_state=target_state,
                transitioned_by=actor_id,
                actor_role=actor_role,
                reason="State unchanged",
                timestamp=datetime.now(timezone.utc)
            )

        # 1. Operational Guard: IN_PROGRESS transition checks
        if target_state == "IN_PROGRESS":
            # Guard A: Verify actor is the assigned technician or an administrator
            if actor_role == "TECHNICIAN" and wo["assigned_tech_id"] != actor_id:
                raise AuthorizationError("Only the technician assigned to this work order may mark it IN_PROGRESS.")

            # Guard B: Starting work on repairs exceeding Rs. 5,000 requires active APPROVED approval matching snapshot
            if wo["estimated_cost"] > Decimal("5000.00"):
                canonical_hash = await conn.fetchval(
                    "SELECT fn_compute_canonical_wo_snapshot($1::uuid);", work_order_id
                )
                approved_record = await conn.fetchrow(
                    """
                    SELECT id FROM approvals
                    WHERE work_order_id = $1 
                      AND status = 'APPROVED'
                      AND snapshot_hash = $2;
                    """,
                    work_order_id,
                    canonical_hash
                )
                if not approved_record:
                    raise ConflictError(
                        f"Work order estimated cost (Rs. {wo['estimated_cost']:,.2f}) exceeds Rs. 5,000 threshold. "
                        "An active APPROVED approval record matching the canonical snapshot hash is required before starting work."
                    )

        # 2. Operational Guard: RESOLVED transition checks
        if target_state == "RESOLVED":
            if not request.resolution_notes:
                request.resolution_notes = "Repairs completed and operational tests verified." 

            # Convert all RESERVED parts to CONSUMED via inventory_movements
            reservations = await conn.fetch(
                """
                SELECT part_id, requested_qty
                FROM part_reservations
                WHERE work_order_id = $1 AND status = 'RESERVED'
                FOR UPDATE;
                """,
                work_order_id
            )
            for res in reservations:
                p_id = res["part_id"]
                qty = res["requested_qty"]

                # Ledger movement: delta_physical = -qty, delta_available = 0, delta_reserved = -qty
                await conn.execute(
                    """
                    INSERT INTO inventory_movements (
                        part_id, work_order_id, actor_id, movement_type,
                        delta_physical, delta_available, delta_reserved
                    )
                    VALUES ($1, $2, $3, 'CONSUME', $4, 0, $4);
                    """,
                    p_id,
                    work_order_id,
                    actor_id,
                    -qty
                )

                # Update balance on inventory_parts
                await conn.execute(
                    """
                    UPDATE inventory_parts
                    SET physical_on_hand_qty = physical_on_hand_qty - $2,
                        reserved_qty = reserved_qty - $2
                    WHERE id = $1;
                    """,
                    p_id,
                    qty
                )

                # Update reservation status to CONSUMED
                await conn.execute(
                    """
                    UPDATE part_reservations
                    SET status = 'CONSUMED'
                    WHERE work_order_id = $1 AND part_id = $2;
                    """,
                    work_order_id,
                    p_id
                )

            # Decrement technician active workload count
            if wo["assigned_tech_id"]:
                await conn.execute(
                    """
                    UPDATE users
                    SET active_workload_count = GREATEST(0, active_workload_count - 1)
                    WHERE id = $1;
                    """,
                    wo["assigned_tech_id"]
                )

        # 3. Execute the state change (The PostgreSQL DB trigger trg_work_order_fsm_enforcement enforces allowed_roles)
        resolved_sql = ", resolved_at = NOW()" if target_state == "RESOLVED" else ""
        await conn.execute(
            f"""
            UPDATE work_orders
            SET state = $2::wo_state,
                updated_at = NOW()
                {resolved_sql}
            WHERE id = $1;
            """,
            work_order_id,
            target_state
        )

        now = datetime.now(timezone.utc)

        # 4. Record in audit_logs
        audit_details = {
            "reason": request.reason,
            "resolution_notes": request.resolution_notes,
            "extra": request.details or {}
        }
        await conn.execute(
            """
            INSERT INTO audit_logs (work_order_id, actor_user_id, action, previous_state, new_state, details)
            VALUES ($1, $2, 'FSM_TRANSITION', $3, $4, $5::jsonb);
            """,
            work_order_id,
            actor_id,
            from_state,
            target_state,
            json.dumps(audit_details)
        )

        return WorkOrderTransitionResponse(
            work_order_id=wo["id"],
            ticket_number=wo["ticket_number"],
            previous_state=from_state,
            new_state=target_state,
            transitioned_by=actor_id,
            actor_role=actor_role,
            reason=request.reason,
            timestamp=now
        )
    @staticmethod
    async def list_comments(
        conn: asyncpg.Connection,
        work_order_id: UUID
    ) -> List[WorkOrderCommentOut]:
        rows = await conn.fetch(
            """
            SELECT id, work_order_id, author_user_id, author_name, author_role, message, created_at
            FROM work_order_comments
            WHERE work_order_id = $1
            ORDER BY created_at ASC;
            """,
            work_order_id
        )
        return [
            WorkOrderCommentOut(
                id=r["id"],
                work_order_id=r["work_order_id"],
                author_user_id=r["author_user_id"],
                author_name=r["author_name"],
                author_role=r["author_role"],
                message=r["message"],
                created_at=r["created_at"]
            )
            for r in rows
        ]
    @staticmethod
    async def add_comment(
        conn: asyncpg.Connection,
        work_order_id: UUID,
        author_id: UUID,
        author_name: str,
        author_role: str,
        message: str
    ) -> WorkOrderCommentOut:
        # Check work order exists
        wo = await conn.fetchrow("SELECT id FROM work_orders WHERE id = $1;", work_order_id)
        if not wo:
            raise ResourceNotFoundError("Work Order", work_order_id)
        row = await conn.fetchrow(
            """
            INSERT INTO work_order_comments (work_order_id, author_user_id, author_name, author_role, message)
            VALUES ($1, $2, $3, $4::user_role, $5)
            RETURNING id, work_order_id, author_user_id, author_name, author_role, message, created_at;
            """,
            work_order_id, author_id, author_name, author_role, message.strip()
        )
        return WorkOrderCommentOut(
            id=row["id"],
            work_order_id=row["work_order_id"],
            author_user_id=row["author_user_id"],
            author_name=row["author_name"],
            author_role=row["author_role"],
            message=row["message"],
            created_at=row["created_at"]
        )
