import json
from uuid import UUID
from typing import List, Optional
from datetime import datetime
import asyncpg
from app.core.exceptions import (
    ResourceNotFoundError,
    InvariantViolationError,
    PermissionDeniedError,
)
from app.modules.approvals.schemas import ApprovalResponse


class ApprovalsService:

    @staticmethod
    async def list_approvals(
        conn: asyncpg.Connection,
        status: Optional[str] = None
    ) -> List[ApprovalResponse]:
        query = """
            SELECT a.id, a.work_order_id, wo.ticket_number, wo.raw_description AS work_order_description,
                   a.approval_type, a.requested_by_user_id, u_req.full_name AS requested_by_name,
                   a.approved_by_user_id, u_app.full_name AS approved_by_name,
                   a.requested_amount, a.snapshot_hash, a.status,
                   a.invalidation_reason, a.created_at, a.decided_at
            FROM approvals a
            JOIN work_orders wo ON wo.id = a.work_order_id
            JOIN users u_req ON u_req.id = a.requested_by_user_id
            LEFT JOIN users u_app ON u_app.id = a.approved_by_user_id
            WHERE ($1::text IS NULL OR a.status = $1)
            ORDER BY a.created_at DESC;
        """
        rows = await conn.fetch(query, status)
        return [
            ApprovalResponse(
                id=r["id"],
                work_order_id=r["work_order_id"],
                ticket_number=r["ticket_number"],
                work_order_description=r["work_order_description"],
                approval_type=r["approval_type"],
                requested_by_user_id=r["requested_by_user_id"],
                requested_by_name=r["requested_by_name"],
                approved_by_user_id=r["approved_by_user_id"],
                approved_by_name=r["approved_by_name"],
                requested_amount=float(r["requested_amount"]),
                snapshot_hash=r["snapshot_hash"],
                status=r["status"],
                invalidation_reason=r["invalidation_reason"],
                created_at=r["created_at"],
                decided_at=r["decided_at"]
            )
            for r in rows
        ]

    @staticmethod
    async def process_decision(
        conn: asyncpg.Connection,
        approval_id: UUID,
        decision: str,  # 'APPROVED' or 'REJECTED'
        actor_id: UUID,
        actor_role: str,
        notes: Optional[str] = None
    ) -> ApprovalResponse:
        row = await conn.fetchrow(
            """
            SELECT a.id, a.work_order_id, a.approval_type, a.requested_by_user_id,
                   a.requested_amount, a.snapshot_hash, a.status,
                   wo.ticket_number, wo.reporter_user_id, wo.assigned_tech_id,
                   wo.state AS wo_state
            FROM approvals a
            JOIN work_orders wo ON wo.id = a.work_order_id
            WHERE a.id = $1
            FOR UPDATE;
            """,
            approval_id
        )
        if not row:
            raise ResourceNotFoundError("ApprovalRecord", str(approval_id))

        if row["status"] != "PENDING":
            raise InvariantViolationError("Approval State Invariant", f"Approval {approval_id} is already in state '{row['status']}'.")

        # 1. Separation of Duties checks
        # SYS_ADMIN has emergency administrative override capability.
        # For all other roles, strictly enforce Separation of Duties.
        if actor_role != "SYS_ADMIN":
            if actor_id == row["requested_by_user_id"]:
                raise PermissionDeniedError("Separation of Duties: Requester cannot approve or reject their own approval request. Switch user role to approve.")

            if actor_id == row["reporter_user_id"]:
                raise PermissionDeniedError("Separation of Duties: Original ticket reporter cannot act as approver. Switch user role to approve.")

            if actor_id == row["assigned_tech_id"]:
                raise PermissionDeniedError("Separation of Duties: Assigned technician cannot act as approver. Switch user role to approve.")

        # 2. Authority Limit Check: Dept Manager limit is Rs. 15,000
        amount = float(row["requested_amount"])
        if actor_role == "DEPT_MANAGER" and amount > 15000.0:
            raise PermissionDeniedError(
                f"Delegation of Authority: Department Manager approval limit is Rs. 15,000.00. "
                f"Request amount Rs. {amount:.2f} requires Facilities Admin or Procurement Approver."
            )

        # 3. Snapshot hash verification
        current_hash = await conn.fetchval(
            "SELECT fn_compute_canonical_wo_snapshot($1::uuid);",
            row["work_order_id"]
        )
        if current_hash != row["snapshot_hash"]:
            # Auto invalidate
            await conn.execute(
                """
                UPDATE approvals
                SET status = 'INVALIDATED_BY_CHANGE',
                    invalidation_reason = 'Scope mutated after approval request: hash mismatch.',
                    decided_at = NOW()
                WHERE id = $1;
                """,
                approval_id
            )
            raise InvariantViolationError(
                "Scope Snapshot Invariant",
                "Work order scope has mutated since approval was requested. Record has been invalidated."
            )

        # 4. Apply decision
        now = datetime.now()
        wo_id = row["work_order_id"]

        if decision == "APPROVED":
            await conn.execute(
                """
                UPDATE approvals
                SET status = 'APPROVED',
                    approved_by_user_id = $2,
                    decided_at = NOW()
                WHERE id = $1;
                """,
                approval_id,
                actor_id
            )

            # Transition work order to APPROVED_READY if in PENDING_APPROVAL
            if row["wo_state"] == "PENDING_APPROVAL":
                await conn.execute(
                    """
                    UPDATE work_orders
                    SET state = 'APPROVED_READY',
                        updated_at = NOW()
                    WHERE id = $1;
                    """,
                    wo_id
                )

            action_name = "APPROVAL_GRANTED"
        else:
            await conn.execute(
                """
                UPDATE approvals
                SET status = 'REJECTED',
                    approved_by_user_id = $2,
                    invalidation_reason = $3,
                    decided_at = NOW()
                WHERE id = $1;
                """,
                approval_id,
                actor_id,
                notes or "Rejected by operational authority."
            )
            action_name = "APPROVAL_REJECTED"

        # 5. Audit Log
        await conn.execute(
            """
            INSERT INTO audit_logs (work_order_id, actor_user_id, action, previous_state, new_state, details)
            VALUES ($1, $2, $3, $4, $5, $6::jsonb);
            """,
            wo_id,
            actor_id,
            action_name,
            row["status"],
            decision,
            json.dumps({
                "approval_id": str(approval_id),
                "approval_type": row["approval_type"],
                "amount": amount,
                "notes": notes
            })
        )

        # Return updated record
        updated_list = await ApprovalsService.list_approvals(conn, status=decision)
        for item in updated_list:
            if item.id == approval_id:
                return item

        raise ResourceNotFoundError("UpdatedApproval", str(approval_id))
