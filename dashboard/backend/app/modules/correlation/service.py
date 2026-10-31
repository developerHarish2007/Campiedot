import json
from uuid import UUID, uuid4
from typing import Dict, Any, Optional
import asyncpg


class CorrelationService:

    @staticmethod
    async def correlate_incident(
        conn: asyncpg.Connection,
        work_order_id: UUID,
        target_node_id: Optional[UUID],
        category: Optional[str],
        actor_id: Optional[UUID] = None
    ) -> Dict[str, Any]:
        """
        Executes Two-Stage Incident Correlation:
        - Stage A: Duplicate room/asset suppression.
        - Stage B: Upstream Topological DAG correlation & Master Infrastructure Ticket spawning.
        """
        if not target_node_id or not category:
            return {"action": "INDEPENDENT_INCIDENT", "work_order_id": work_order_id}

        # ----------------------------------------------------------------------
        # STAGE A: EXACT SAME NODE & CATEGORY DUPLICATE SUPPRESSION
        # ----------------------------------------------------------------------
        existing_node_master = await conn.fetchrow(
            """
            SELECT id, ticket_number, correlator_reporter_count, state
            FROM work_orders
            WHERE target_node_id = $1
              AND category = $2::issue_category
              AND state NOT IN ('RESOLVED', 'CLOSED', 'MERGED_DUPLICATE')
              AND id <> $3
            ORDER BY created_at ASC
            LIMIT 1
            FOR UPDATE;
            """,
            target_node_id,
            category,
            work_order_id
        )

        if existing_node_master:
            master_id = existing_node_master["id"]
            new_count = existing_node_master["correlator_reporter_count"] + 1

            # Update this work order to MERGED_DUPLICATE and link to master
            await conn.execute(
                """
                UPDATE work_orders
                SET state = 'MERGED_DUPLICATE',
                    parent_master_wo_id = $2,
                    updated_at = NOW()
                WHERE id = $1;
                """,
                work_order_id,
                master_id
            )

            # Increment count on master
            await conn.execute(
                """
                UPDATE work_orders
                SET correlator_reporter_count = $2,
                    updated_at = NOW()
                WHERE id = $1;
                """,
                master_id,
                new_count
            )

            # Audit record
            await conn.execute(
                """
                INSERT INTO audit_logs (work_order_id, actor_user_id, action, previous_state, new_state, details)
                VALUES ($1, $2, 'STAGE_A_DUPLICATE_MERGE', 'INGESTED', 'MERGED_DUPLICATE', $3::jsonb);
                """,
                work_order_id,
                actor_id,
                json.dumps({
                    "master_work_order_id": str(master_id),
                    "master_ticket_number": existing_node_master["ticket_number"],
                    "total_reporters": new_count
                })
            )

            return {
                "action": "MERGED_DUPLICATE",
                "master_work_order_id": master_id,
                "master_ticket_number": existing_node_master["ticket_number"],
                "reporter_count": new_count
            }

        # ----------------------------------------------------------------------
        # STAGE B: TOPOLOGICAL DAG CORRELATION (UPSTREAM PARENT HIERARCHY)
        # ----------------------------------------------------------------------
        upstream_parents = await conn.fetch(
            """
            SELECT parent_node_id
            FROM node_dependencies
            WHERE child_node_id = $1 AND dependency_domain = $2::issue_category;
            """,
            target_node_id,
            category
        )

        for p_row in upstream_parents:
            parent_id = p_row["parent_node_id"]

            # Query all sibling children sharing this upstream parent
            sibling_rows = await conn.fetch(
                """
                SELECT child_node_id
                FROM node_dependencies
                WHERE parent_node_id = $1 AND dependency_domain = $2::issue_category;
                """,
                parent_id,
                category
            )
            sibling_ids = [r["child_node_id"] for r in sibling_rows]

            # Find active work orders across sibling nodes within the last 45 minutes
            active_sibling_wos = await conn.fetch(
                """
                SELECT id, target_node_id, ticket_number, state
                FROM work_orders
                WHERE target_node_id = ANY($1::uuid[])
                  AND category = $2::issue_category
                  AND state NOT IN ('RESOLVED', 'CLOSED', 'MERGED_DUPLICATE')
                  AND created_at >= NOW() - INTERVAL '45 minutes'
                FOR UPDATE;
                """,
                sibling_ids,
                category
            )

            # Count distinct affected sibling nodes (including current node)
            distinct_nodes = {r["target_node_id"] for r in active_sibling_wos}
            distinct_nodes.add(target_node_id)

            if len(distinct_nodes) >= 2:
                # Upstream failure detected across >= 2 sibling nodes!
                parent_node = await conn.fetchrow(
                    "SELECT node_code, name, building_code FROM campus_nodes WHERE id = $1;", parent_id
                )

                # Check if a Master Infrastructure Ticket already exists on the parent node
                existing_parent_master = await conn.fetchrow(
                    """
                    SELECT id, ticket_number, correlator_reporter_count
                    FROM work_orders
                    WHERE target_node_id = $1
                      AND category = $2::issue_category
                      AND state NOT IN ('RESOLVED', 'CLOSED')
                    LIMIT 1
                    FOR UPDATE;
                    """,
                    parent_id,
                    category
                )

                if existing_parent_master:
                    master_wo_id = existing_parent_master["id"]
                    new_count = existing_parent_master["correlator_reporter_count"] + 1

                    # Link current work order as child
                    await conn.execute(
                        """
                        UPDATE work_orders
                        SET parent_master_wo_id = $2,
                            updated_at = NOW()
                        WHERE id = $1;
                        """,
                        work_order_id,
                        master_wo_id
                    )

                    await conn.execute(
                        """
                        UPDATE work_orders
                        SET correlator_reporter_count = $2,
                            updated_at = NOW()
                        WHERE id = $1;
                        """,
                        master_wo_id,
                        new_count
                    )

                    await conn.execute(
                        """
                        INSERT INTO audit_logs (work_order_id, actor_user_id, action, previous_state, new_state, details)
                        VALUES ($1, $2, 'STAGE_B_DAG_CHILD_LINKED', 'INGESTED', 'TRIAGED', $3::jsonb);
                        """,
                        work_order_id,
                        actor_id,
                        json.dumps({
                            "master_parent_node": parent_node["node_code"],
                            "master_work_order_id": str(master_wo_id),
                        })
                    )

                    return {
                        "action": "DAG_CORRELATED",
                        "master_infrastructure_wo_id": master_wo_id,
                        "upstream_parent_node": parent_node["node_code"],
                        "affected_siblings_count": len(distinct_nodes)
                    }

                else:
                    # Spawn new Master Infrastructure Incident on the upstream parent node
                    admin_user_id = await conn.fetchval(
                        "SELECT id FROM users WHERE role = 'FACILITIES_ADMIN' LIMIT 1;"
                    )
                    dept_id = await conn.fetchval(
                        "SELECT id FROM departments WHERE code = 'DEPT-ADMIN' LIMIT 1;"
                    )

                    master_desc = (
                        f"MASTER INFRASTRUCTURE INCIDENT: Upstream {parent_node['name']} ({parent_node['node_code']}) "
                        f"failure causing concurrent {category} disruptions across {len(distinct_nodes)} sibling nodes."
                    )

                    master_row = await conn.fetchrow(
                        """
                        INSERT INTO work_orders (
                            conversation_thread_id, reporter_user_id, target_node_id,
                            category, reporter_urgency, calculated_priority, impact_score,
                            state, raw_description, ai_summary, department_id,
                            correlator_reporter_count
                        )
                        VALUES ($1, $2, $3, $4::issue_category, 'P1_HIGH'::priority_level, 'P0_CRITICAL'::priority_level, 80,
                                'TRIAGED'::wo_state, $5, $6, $7, $8)
                        RETURNING id, ticket_number;
                        """,
                        f"thread-master-{uuid4().hex[:10]}",
                        admin_user_id,
                        parent_id,
                        category,
                        master_desc,
                        master_desc,
                        dept_id,
                        len(active_sibling_wos) + 1
                    )

                    master_wo_id = master_row["id"]

                    # Link all sibling tickets to this new master ticket
                    all_ticket_ids = [r["id"] for r in active_sibling_wos] + [work_order_id]
                    await conn.execute(
                        """
                        UPDATE work_orders
                        SET parent_master_wo_id = $2,
                            updated_at = NOW()
                        WHERE id = ANY($1::uuid[]);
                        """,
                        all_ticket_ids,
                        master_wo_id
                    )

                    # Audit record
                    await conn.execute(
                        """
                        INSERT INTO audit_logs (work_order_id, actor_user_id, action, previous_state, new_state, details)
                        VALUES ($1, $2, 'STAGE_B_DAG_MASTER_SPAWNED', NULL, 'TRIAGED', $3::jsonb);
                        """,
                        master_wo_id,
                        actor_id or admin_user_id,
                        json.dumps({
                            "upstream_node": parent_node["node_code"],
                            "linked_children_count": len(all_ticket_ids),
                            "affected_nodes": list(distinct_nodes)
                        }, default=str)
                    )

                    return {
                        "action": "DAG_CORRELATED",
                        "master_infrastructure_wo_id": master_wo_id,
                        "upstream_parent_node": parent_node["node_code"],
                        "affected_siblings_count": len(distinct_nodes)
                    }

        return {"action": "INDEPENDENT_INCIDENT", "work_order_id": work_order_id}

