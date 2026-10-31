from typing import List, Optional, Tuple
from uuid import UUID
import asyncpg
from app.core.exceptions import ResourceNotFoundError, ConflictError
from app.modules.ai.agents import WorkerDispatchAgent, AntiHallucinationAgent
from app.modules.integrations.resend_client import ResendEmailService
from app.modules.staffing.schemas import (
    TechnicianScoreBreakdown,
    AssignTechnicianResponse,
    DynamicReassignmentItem,
    ToggleAvailabilityResponse,
    TechnicianSummary,
    WorkerDetail,
)


class StaffingService:

    @staticmethod
    async def score_eligible_technicians(
        conn: asyncpg.Connection,
        category: str,
        target_building: Optional[str] = None,
        exclude_tech_id: Optional[UUID] = None
    ) -> List[TechnicianScoreBreakdown]:
        """
        Executes deterministic technician scoring.
        Applies hard filters: role == TECHNICIAN, is_available == TRUE,
        matching category skill, active shift window @> NOW(), workload < max.
        Applies formula: Score = (Skill * 15.0) + ((1 - load/max) * 25.0) + (Proximity * 15.0).
        """
        query = """
            SELECT u.id, u.full_name, u.email, u.active_workload_count,
                   u.max_concurrent_workload, u.base_building_code,
                   sk.proficiency_level
            FROM users u
            JOIN staff_skills sk ON sk.user_id = u.id AND sk.skill = $1::issue_category
            WHERE u.role = 'TECHNICIAN'
              AND u.is_available = TRUE
              AND u.active_workload_count < u.max_concurrent_workload
              AND EXISTS (
                  SELECT 1 FROM staff_shifts ss
                  WHERE ss.user_id = u.id AND ss.shift_window @> NOW()
              )
        """
        params = [category]
        if exclude_tech_id:
            params.append(exclude_tech_id)
            query += f" AND u.id <> ${len(params)}"

        rows = await conn.fetch(query, *params)
        scored_candidates = []

        for r in rows:
            skill_prof = r["proficiency_level"]
            active_load = r["active_workload_count"]
            max_load = r["max_concurrent_workload"]
            base_bldg = r["base_building_code"]

            skill_score = skill_prof * 15.0
            workload_score = (1.0 - (float(active_load) / float(max_load))) * 25.0
            proximity_bonus = 15.0 if (target_building and base_bldg == target_building) else 0.0
            total_score = skill_score + workload_score + proximity_bonus

            explanation = (
                f"{r['full_name']} (proficiency {skill_prof}/5, workload {active_load}/{max_load}, "
                f"proximity bonus {proximity_bonus:.0f} pts) scored {total_score:.1f}"
            )

            scored_candidates.append(
                TechnicianScoreBreakdown(
                    technician_id=r["id"],
                    full_name=r["full_name"],
                    email=r["email"],
                    skill_proficiency=skill_prof,
                    active_workload=active_load,
                    max_workload=max_load,
                    base_building=base_bldg,
                    proximity_bonus=proximity_bonus,
                    total_score=round(total_score, 2),
                    explanation=explanation
                )
            )

        scored_candidates.sort(key=lambda x: x.total_score, reverse=True)
        return scored_candidates

    @staticmethod
    async def assign_technician(
        conn: asyncpg.Connection,
        work_order_id: UUID,
        technician_id: Optional[UUID] = None,
        worker_name: Optional[str] = None,
        worker_email: Optional[str] = None,
        worker_role: Optional[str] = None,
        actor_id: Optional[UUID] = None
    ) -> AssignTechnicianResponse:
        """
        Assigns or reassigns a technician/worker to a work order.
        Supports adding/registering a worker by name, email, and role (electrician, plumber, etc.),
        direct assignment by technician_id, or automatic deterministic dispatch scoring.
        """
        # Role normalization map
        ROLE_MAP = {
            "electrician": "ELECTRICAL",
            "electrical": "ELECTRICAL",
            "plumber": "PLUMBING",
            "plumbing": "PLUMBING",
            "network": "NETWORK",
            "it": "NETWORK",
            "carpenter": "STRUCTURAL_SAFETY",
            "structural": "STRUCTURAL_SAFETY",
            "safety": "STRUCTURAL_SAFETY",
            "sos": "SOS",
            "emergency": "SOS",
            "medical": "SOS",
            "doctor": "SOS",
            "nurse": "SOS",
            "firstaid": "SOS",
            "first_aid": "SOS",
            "first aid": "SOS",
            "ambulance": "SOS",
            "sweeper": "SWEEPER",
            "cleaning": "SWEEPER",
            "cleaner": "SWEEPER",
            "janitor": "SWEEPER",
            "sanitation": "SWEEPER",
            "housekeeping": "SWEEPER",
            "sweep": "SWEEPER",
            "hvac": "ELECTRICAL",
            "ac": "ELECTRICAL",
            "cooling": "ELECTRICAL",
            "av": "NETWORK",
            "audio": "NETWORK",
        }

        target_role = None
        if worker_role:
            clean_role = worker_role.strip().lower()
            target_role = ROLE_MAP.get(clean_role, worker_role.upper())

        # 1. Fetch work order details
        wo = await conn.fetchrow(
            """
            SELECT wo.id, wo.ticket_number, wo.category, wo.state, wo.assigned_tech_id,
                   wo.target_node_id, wo.raw_description, wo.calculated_priority,
                   cn.building_code, cn.node_code, cn.name AS node_name
            FROM work_orders wo
            LEFT JOIN campus_nodes cn ON wo.target_node_id = cn.id
            WHERE wo.id = $1
            FOR UPDATE OF wo;
            """,
            work_order_id
        )
        if not wo:
            raise ResourceNotFoundError("Work Order", work_order_id)

        category = wo["category"]
        if not category and target_role:
            category = target_role
            await conn.execute(
                "UPDATE work_orders SET category = $2::issue_category WHERE id = $1;",
                work_order_id, category
            )

        if not category and not target_role and not worker_name:
            raise ConflictError("Work order must have a categorized domain before technician assignment.")

        target_building = wo["building_code"]
        previous_tech_id = wo["assigned_tech_id"]

        selected_tech = None
        score = 0.0
        explanation = ""

        # Case A: Worker Name and Email provided (register / assign custom worker)
        if worker_name and worker_email:
            worker_email_clean = worker_email.strip().lower()
            worker_name_clean = worker_name.strip()
            trade_role = target_role or category or "ELECTRICAL"

            existing_user = await conn.fetchrow(
                "SELECT id, full_name, email, role FROM users WHERE LOWER(email) = $1;",
                worker_email_clean
            )
            if existing_user:
                tech_id = existing_user["id"]
                await conn.execute(
                    "UPDATE users SET full_name = $2, role = 'TECHNICIAN', is_available = TRUE WHERE id = $1;",
                    tech_id, worker_name_clean
                )
            else:
                tech_id = await conn.fetchval(
                    """
                    INSERT INTO users (id, email, full_name, role, is_available, max_concurrent_workload, active_workload_count)
                    VALUES (gen_random_uuid(), $1, $2, 'TECHNICIAN', TRUE, 5, 0)
                    RETURNING id;
                    """,
                    worker_email_clean, worker_name_clean
                )

            # Ensure trade skill registered in staff_skills
            await conn.execute(
                """
                INSERT INTO staff_skills (user_id, skill, proficiency_level)
                VALUES ($1, $2::issue_category, 5)
                ON CONFLICT (user_id, skill) DO UPDATE SET proficiency_level = 5;
                """,
                tech_id, trade_role
            )

            # Ensure active shift exists
            await conn.execute(
                """
                INSERT INTO staff_shifts (user_id, shift_window)
                VALUES ($1, tstzrange(NOW() - INTERVAL '1 day', NOW() + INTERVAL '30 days'))
                ON CONFLICT DO NOTHING;
                """,
                tech_id
            )

            if not category:
                category = trade_role
                await conn.execute(
                    "UPDATE work_orders SET category = $2::issue_category WHERE id = $1;",
                    work_order_id, category
                )

            selected_tech = {
                "id": tech_id,
                "full_name": worker_name_clean,
                "email": worker_email_clean,
                "role": trade_role
            }
            score = 100.0
            explanation = f"Manual worker assignment: {worker_name_clean} ({trade_role}) <{worker_email_clean}>."

        # Case B: Direct assignment by existing technician_id
        elif technician_id is not None:
            tech_check = await conn.fetchrow(
                """
                SELECT u.id, u.full_name, u.email, u.is_available, u.active_workload_count,
                       u.max_concurrent_workload, u.base_building_code,
                       sk.proficiency_level,
                       sk.skill::text AS primary_skill,
                       EXISTS (
                           SELECT 1 FROM staff_shifts ss
                           WHERE ss.user_id = u.id AND ss.shift_window @> NOW()
                       ) AS on_shift
                FROM users u
                LEFT JOIN staff_skills sk ON sk.user_id = u.id AND sk.skill = $2::issue_category
                WHERE u.id = $1;
                """,
                technician_id,
                category or "ELECTRICAL"
            )
            if not tech_check:
                raise ResourceNotFoundError("Technician", technician_id)

            # Auto-ensure skill & shift for administrative assignment
            if tech_check["proficiency_level"] is None and category:
                await conn.execute(
                    """
                    INSERT INTO staff_skills (user_id, skill, proficiency_level)
                    VALUES ($1, $2::issue_category, 4)
                    ON CONFLICT (user_id, skill) DO NOTHING;
                    """,
                    technician_id, category
                )
            if not tech_check["on_shift"]:
                await conn.execute(
                    """
                    INSERT INTO staff_shifts (user_id, shift_window)
                    VALUES ($1, tstzrange(NOW() - INTERVAL '1 day', NOW() + INTERVAL '30 days'))
                    ON CONFLICT DO NOTHING;
                    """,
                    technician_id
                )

            selected_tech = {
                "id": tech_check["id"],
                "full_name": tech_check["full_name"],
                "email": tech_check["email"],
                "role": target_role or tech_check["primary_skill"] or category
            }
            score = 100.0
            explanation = f"Direct assignment by authorized manager: {tech_check['full_name']}."

        else:
            # Case C: Deterministic Auto-Assignment
            candidates = await StaffingService.score_eligible_technicians(
                conn, category=category, target_building=target_building
            )
            if not candidates:
                raise ConflictError(f"No eligible technician currently available on shift for category '{category}'.")

            top_candidate = candidates[0]
            selected_tech = {
                "id": top_candidate.technician_id,
                "full_name": top_candidate.full_name,
                "email": top_candidate.email,
                "role": category
            }
            score = top_candidate.total_score
            explanation = top_candidate.explanation

        new_tech_id = selected_tech["id"]

        # 2. Update workload counts
        if previous_tech_id and previous_tech_id != new_tech_id:
            await conn.execute(
                """
                UPDATE users
                SET active_workload_count = GREATEST(0, active_workload_count - 1)
                WHERE id = $1;
                """,
                previous_tech_id
            )

        if previous_tech_id != new_tech_id:
            await conn.execute(
                """
                UPDATE users
                SET active_workload_count = active_workload_count + 1
                WHERE id = $1;
                """,
                new_tech_id
            )

        # 3. Update work order state and technician
        new_state = "ASSIGNED" if wo["state"] in ("INGESTED", "TRIAGED", "AWAITING_CLARIFICATION") else wo["state"]
        await conn.execute(
            """
            UPDATE work_orders
            SET assigned_tech_id = $2,
                state = $3,
                updated_at = NOW()
            WHERE id = $1;
            """,
            work_order_id,
            new_tech_id,
            new_state
        )

        # 4. Audit Log
        actor = actor_id or new_tech_id
        await conn.execute(
            """
            INSERT INTO audit_logs (work_order_id, actor_user_id, action, previous_state, new_state, details)
            VALUES ($1, $2, 'TECHNICIAN_ASSIGNED', $3, $4, $5::jsonb);
            """,
            work_order_id,
            actor,
            wo["state"],
            new_state,
            f'{{"assigned_tech_id": "{new_tech_id}", "tech_name": "{selected_tech["full_name"]}", "score": {score}, "explanation": "{explanation}"}}'
        )

        # 5. Multi-Agent Worker Notification Pipeline via Resend API
        # Only send emails to designated workers:
        # Electrical Worker: arunak0787@gmail.com
        # Structural Safety Worker: jeevadarwin007@gmail.com
        EMAIL_NOTIFICATION_ALLOWED_WORKERS = {
            "arunak0787@gmail.com",
            "jeevadarwin007@gmail.com"
        }

        email_dispatched = False
        email_id = None
        email_subject = None

        target_raw_email = (selected_tech.get("email") or "").strip().lower()
        if target_raw_email in EMAIL_NOTIFICATION_ALLOWED_WORKERS:
            target_worker_email = target_raw_email
            target_worker_name = selected_tech["full_name"]
            target_worker_role = selected_tech.get("role") or category or "TECHNICIAN"

            # Agent 1: Generate tailored dispatch email
            dispatch_draft = await WorkerDispatchAgent.generate_dispatch_email(
                ticket_number=wo["ticket_number"] if wo["ticket_number"] else 0,
                category=category or "GENERAL_MAINTENANCE",
                raw_description=wo["raw_description"] or "Assigned campus maintenance ticket",
                location_hint=wo["node_code"] if wo["node_code"] else None,
                worker_name=target_worker_name,
                worker_role=target_worker_role,
                urgency=wo["calculated_priority"] if wo["calculated_priority"] else "P2_MEDIUM"
            )

            # Agent 3: Anti-Hallucination Grounding & Safety Audit
            verified_dispatch = await AntiHallucinationAgent.verify_and_ground_dispatch(
                dispatch_draft, worker_role=target_worker_role
            )

            # Send via Resend Email Service
            resend_result = await ResendEmailService.send_email(
                to_email=target_worker_email,
                subject=verified_dispatch.subject,
                html_body=verified_dispatch.html_body,
                text_body=verified_dispatch.text_body
            )

            email_dispatched = resend_result.get("success", False)
            email_id = resend_result.get("id")
            email_subject = verified_dispatch.subject

            # Record in outbound_notifications table
            delivery_status = "DELIVERED" if email_dispatched else "PENDING"
            await conn.execute(
                """
                INSERT INTO outbound_notifications (recipient_user_id, recipient_email, channel, subject, body, work_order_id, delivery_status)
                VALUES ($1, $2, 'EMAIL', $3, $4, $5, $6);
                """,
                new_tech_id,
                target_worker_email,
                verified_dispatch.subject,
                verified_dispatch.html_body,
                work_order_id,
                delivery_status
            )

        return AssignTechnicianResponse(
            work_order_id=work_order_id,
            assigned_tech_id=new_tech_id,
            assigned_tech_name=selected_tech["full_name"],
            assigned_tech_email=selected_tech["email"],
            assigned_tech_role=selected_tech.get("role") or category,
            score=score,
            explanation=explanation,
            work_order_state=new_state,
            email_dispatched=email_dispatched,
            email_dispatch_id=email_id,
            email_subject=email_subject
        )

    @staticmethod
    async def list_technicians(conn: asyncpg.Connection) -> List[TechnicianSummary]:
        """Lists all technicians registered with their skills, workload and availability."""
        rows = await conn.fetch(
            """
            SELECT u.id, u.full_name, u.email, u.is_available, u.active_workload_count,
                   COALESCE(ARRAY_AGG(sk.skill::text) FILTER (WHERE sk.skill IS NOT NULL), '{}') AS roles
            FROM users u
            LEFT JOIN staff_skills sk ON sk.user_id = u.id
            WHERE u.role = 'TECHNICIAN'
            GROUP BY u.id, u.full_name, u.email, u.is_available, u.active_workload_count
            ORDER BY u.full_name ASC;
            """
        )
        return [
            TechnicianSummary(
                id=r["id"],
                full_name=r["full_name"],
                email=r["email"],
                roles=list(r["roles"]),
                is_available=r["is_available"],
                active_workload_count=r["active_workload_count"]
            )
            for r in rows
        ]

    @staticmethod
    async def toggle_availability(
        conn: asyncpg.Connection,
        technician_id: UUID,
        is_available: bool,
        reason: Optional[str] = None,
        actor_id: Optional[UUID] = None
    ) -> ToggleAvailabilityResponse:
        """
        Toggles technician availability.
        When is_available is toggled to FALSE, automatically finds all active assigned tickets
        and triggers Dynamic Reassignment with the 3-reassignment anti-flap escalation guard.
        """
        tech = await conn.fetchrow(
            "SELECT id, full_name, email, role FROM users WHERE id = $1 FOR UPDATE;", technician_id
        )
        if not tech or tech["role"] != "TECHNICIAN":
            raise ResourceNotFoundError("Technician", technician_id)

        await conn.execute(
            "UPDATE users SET is_available = $2 WHERE id = $1;", technician_id, is_available
        )

        reassignments: List[DynamicReassignmentItem] = []

        if not is_available:
            # Find open work orders assigned to this technician
            open_wos = await conn.fetch(
                """
                SELECT wo.id, wo.ticket_number, wo.category, wo.reassignment_count,
                       wo.state, cn.building_code
                FROM work_orders wo
                LEFT JOIN campus_nodes cn ON wo.target_node_id = cn.id
                WHERE wo.assigned_tech_id = $1
                  AND wo.state IN ('ASSIGNED', 'IN_PROGRESS', 'BLOCKED_PARTS')
                ORDER BY wo.created_at ASC
                FOR UPDATE OF wo;
                """,
                technician_id
            )

            for r in open_wos:
                wo_id = r["id"]
                t_num = r["ticket_number"]
                cat = r["category"]
                bldg = r["building_code"]
                reassign_count = r["reassignment_count"]

                # ANTI-FLAP GUARD: If already reassigned 3 or more times, escalate to admin
                if reassign_count >= 3:
                    # Transition to TRIAGED and clear assigned tech
                    await conn.execute(
                        """
                        UPDATE work_orders
                        SET assigned_tech_id = NULL,
                            state = 'TRIAGED',
                            updated_at = NOW()
                        WHERE id = $1;
                        """,
                        wo_id
                    )
                    # Decrement old tech load
                    await conn.execute(
                        """
                        UPDATE users
                        SET active_workload_count = GREATEST(0, active_workload_count - 1)
                        WHERE id = $1;
                        """,
                        technician_id
                    )
                    # Notify admin
                    admin_id = await conn.fetchval(
                        "SELECT id FROM users WHERE role = 'FACILITIES_ADMIN' LIMIT 1;"
                    )
                    admin_email = await conn.fetchval(
                        "SELECT email FROM users WHERE id = $1;", admin_id
                    )
                    await conn.execute(
                        """
                        INSERT INTO outbound_notifications (recipient_user_id, recipient_email, subject, body, work_order_id)
                        VALUES ($1, $2, $3, $4, $5);
                        """,
                        admin_id,
                        admin_email or "admin@easwari.edu",
                        f"ESCALATION: Ticket #{t_num} Flapping Guard Triggered",
                        f"Work order #{t_num} reached max reassignment limit ({reassign_count} hops). Technician {tech['full_name']} became unavailable. Reverted to TRIAGED for manual dispatch.",
                        wo_id
                    )
                    # Audit log
                    await conn.execute(
                        """
                        INSERT INTO audit_logs (work_order_id, actor_user_id, action, previous_state, new_state, details)
                        VALUES ($1, $2, 'ANTI_FLAP_ESCALATION', $3, 'TRIAGED', $4::jsonb);
                        """,
                        wo_id,
                        actor_id or technician_id,
                        r["state"],
                        f'{{"reason": "Anti-flap guard triggered (hops={reassign_count})"}}'
                    )

                    reassignments.append(
                        DynamicReassignmentItem(
                            work_order_id=wo_id,
                            ticket_number=t_num,
                            previous_tech_id=technician_id,
                            new_tech_id=None,
                            new_tech_name=None,
                            reassignment_count=reassign_count,
                            escalated_to_admin=True,
                            reason=f"Anti-flap guard triggered: reassignment limit ({reassign_count}) reached."
                        )
                    )
                else:
                    # Score remaining available technicians
                    candidates = await StaffingService.score_eligible_technicians(
                        conn, category=cat, target_building=bldg, exclude_tech_id=technician_id
                    )

                    if candidates:
                        next_tech = candidates[0]
                        # Transfer assignment
                        await conn.execute(
                            """
                            UPDATE work_orders
                            SET assigned_tech_id = $2,
                                reassignment_count = reassignment_count + 1,
                                updated_at = NOW()
                            WHERE id = $1;
                            """,
                            wo_id,
                            next_tech.technician_id
                        )
                        # Decrement old tech, increment new tech
                        await conn.execute(
                            """
                            UPDATE users
                            SET active_workload_count = GREATEST(0, active_workload_count - 1)
                            WHERE id = $1;
                            """,
                            technician_id
                        )
                        await conn.execute(
                            """
                            UPDATE users
                            SET active_workload_count = active_workload_count + 1
                            WHERE id = $1;
                            """,
                            next_tech.technician_id
                        )

                        # Audit log
                        await conn.execute(
                            """
                            INSERT INTO audit_logs (work_order_id, actor_user_id, action, previous_state, new_state, details)
                            VALUES ($1, $2, 'DYNAMIC_REASSIGNMENT', $3, $3, $4::jsonb);
                            """,
                            wo_id,
                            actor_id or technician_id,
                            r["state"],
                            f'{{"from_tech": "{tech["full_name"]}", "to_tech": "{next_tech.full_name}", "reassignment_count": {reassign_count + 1}}}'
                        )

                        # Outbox notification to new technician
                        await conn.execute(
                            """
                            INSERT INTO outbound_notifications (recipient_user_id, recipient_email, subject, body, work_order_id)
                            VALUES ($1, $2, $3, $4, $5);
                            """,
                            next_tech.technician_id,
                            next_tech.email,
                            f"Reassigned Ticket #{t_num}",
                            f"Work order #{t_num} has been dynamically reassigned to you. Previous technician unavailable.",
                            wo_id
                        )

                        reassignments.append(
                            DynamicReassignmentItem(
                                work_order_id=wo_id,
                                ticket_number=t_num,
                                previous_tech_id=technician_id,
                                new_tech_id=next_tech.technician_id,
                                new_tech_name=next_tech.full_name,
                                reassignment_count=reassign_count + 1,
                                escalated_to_admin=False,
                                reason=f"Dynamic handoff: {tech['full_name']} unavailable -> dispatched {next_tech.full_name}"
                            )
                        )
                    else:
                        # No alternate technicians on shift: escalate to TRIAGED
                        await conn.execute(
                            """
                            UPDATE work_orders
                            SET assigned_tech_id = NULL,
                                state = 'TRIAGED',
                                reassignment_count = reassignment_count + 1,
                                updated_at = NOW()
                            WHERE id = $1;
                            """,
                            wo_id
                        )
                        await conn.execute(
                            """
                            UPDATE users
                            SET active_workload_count = GREATEST(0, active_workload_count - 1)
                            WHERE id = $1;
                            """,
                            technician_id
                        )
                        reassignments.append(
                            DynamicReassignmentItem(
                                work_order_id=wo_id,
                                ticket_number=t_num,
                                previous_tech_id=technician_id,
                                new_tech_id=None,
                                new_tech_name=None,
                                reassignment_count=reassign_count + 1,
                                escalated_to_admin=True,
                                reason="No alternative technicians currently available on shift."
                            )
                        )

        return ToggleAvailabilityResponse(
            technician_id=technician_id,
            is_available=is_available,
            affected_work_orders_count=len(reassignments),
            reassignments=reassignments
        )

    @staticmethod
    async def register_worker(
        conn: asyncpg.Connection,
        full_name: str,
        email: str,
        role: str,
    ) -> WorkerDetail:
        ROLE_MAP = {
            "electrician": "ELECTRICAL",
            "electrical": "ELECTRICAL",
            "plumber": "PLUMBING",
            "plumbing": "PLUMBING",
            "hvac": "HVAC",
            "ac": "HVAC",
            "cooling": "HVAC",
            "network": "NETWORK",
            "it": "NETWORK",
            "audio": "AV_EQUIPMENT",
            "av": "AV_EQUIPMENT",
            "audiovisual": "AV_EQUIPMENT",
            "carpenter": "STRUCTURAL_SAFETY",
            "structural": "STRUCTURAL_SAFETY",
            "safety": "STRUCTURAL_SAFETY",
        }
        trade_role = ROLE_MAP.get(role.strip().lower(), role.strip().upper())
        valid_roles = ["ELECTRICAL", "HVAC", "PLUMBING", "NETWORK", "AV_EQUIPMENT", "FURNITURE", "STRUCTURAL_SAFETY"]
        if trade_role not in valid_roles:
            trade_role = "ELECTRICAL"

        email_clean = email.strip().lower()
        name_clean = full_name.strip()

        existing = await conn.fetchrow(
            "SELECT id, full_name, email, role FROM users WHERE LOWER(email) = $1;",
            email_clean
        )
        if existing:
            worker_id = existing["id"]
            await conn.execute(
                """
                UPDATE users
                SET full_name = $2, role = 'TECHNICIAN', is_available = TRUE
                WHERE id = $1;
                """,
                worker_id, name_clean
            )
        else:
            worker_id = await conn.fetchval(
                """
                INSERT INTO users (id, email, full_name, role, is_available, max_concurrent_workload, active_workload_count)
                VALUES (gen_random_uuid(), $1, $2, 'TECHNICIAN', TRUE, 5, 0)
                RETURNING id;
                """,
                email_clean, name_clean
            )

        # Register skill
        await conn.execute(
            """
            INSERT INTO staff_skills (user_id, skill, proficiency_level)
            VALUES ($1, $2::issue_category, 5)
            ON CONFLICT (user_id, skill) DO UPDATE SET proficiency_level = 5;
            """,
            worker_id, trade_role
        )

        # Register active shift
        await conn.execute(
            """
            INSERT INTO staff_shifts (user_id, shift_window)
            VALUES ($1, tstzrange(NOW() - INTERVAL '1 day', NOW() + INTERVAL '365 days'));
            """,
            worker_id
        )

        return WorkerDetail(
            id=worker_id,
            full_name=name_clean,
            email=email_clean,
            role=trade_role,
            skills=[trade_role],
            is_available=True,
            active_workload_count=0,
            max_concurrent_workload=5,
        )

    @staticmethod
    async def list_registered_workers(conn: asyncpg.Connection) -> List[WorkerDetail]:
        rows = await conn.fetch(
            """
            SELECT u.id, u.full_name, u.email, u.role, u.is_available,
                   u.active_workload_count, u.max_concurrent_workload,
                   COALESCE(array_agg(sk.skill::text) FILTER (WHERE sk.skill IS NOT NULL), '{}') AS skills
            FROM users u
            LEFT JOIN staff_skills sk ON sk.user_id = u.id
            WHERE u.role = 'TECHNICIAN'
            GROUP BY u.id, u.full_name, u.email, u.role, u.is_available, u.active_workload_count, u.max_concurrent_workload
            ORDER BY u.full_name ASC;
            """
        )
        result = []
        for r in rows:
            primary_role = r["skills"][0] if r["skills"] else "GENERAL"
            result.append(
                WorkerDetail(
                    id=r["id"],
                    full_name=r["full_name"],
                    email=r["email"],
                    role=primary_role,
                    skills=list(r["skills"]),
                    is_available=r["is_available"],
                    active_workload_count=r["active_workload_count"],
                    max_concurrent_workload=r["max_concurrent_workload"]
                )
            )
        return result

    @staticmethod
    async def delete_worker(conn: asyncpg.Connection, worker_id: UUID) -> bool:
        # Check existence
        existing = await conn.fetchrow("SELECT id FROM users WHERE id = $1 AND role = 'TECHNICIAN';", worker_id)
        if not existing:
            raise ResourceNotFoundError("Technician", worker_id)

        # Unassign from any work orders
        await conn.execute("UPDATE work_orders SET assigned_tech_id = NULL WHERE assigned_tech_id = $1;", worker_id)
        # Clear staff skills & shifts
        await conn.execute("DELETE FROM staff_skills WHERE user_id = $1;", worker_id)
        await conn.execute("DELETE FROM staff_shifts WHERE user_id = $1;", worker_id)
        # Clear foreign keys if any
        await conn.execute("UPDATE outbound_notifications SET recipient_user_id = NULL WHERE recipient_user_id = $1;", worker_id)
        await conn.execute("UPDATE audit_logs SET actor_user_id = NULL WHERE actor_user_id = $1;", worker_id)
        # Delete user
        await conn.execute("DELETE FROM users WHERE id = $1;", worker_id)
        return True


