from typing import List, Dict, Any, Optional
from uuid import UUID
from decimal import Decimal
import asyncpg
from app.core.exceptions import ResourceNotFoundError, InventoryShortageError, ConflictError
from app.modules.inventory.schemas import (
    InventoryPartOut,
    ReservePartsRequest,
    ReservePartsResponse,
    PartReservationResult,
    ReceiveStockRequest,
    CreatePartRequest,
)


class InventoryService:

    @staticmethod
    async def list_parts(
        conn: asyncpg.Connection,
        category: Optional[str] = None,
        only_shortages: bool = False
    ) -> List[InventoryPartOut]:
        query = """
            SELECT id, sku, name, category, physical_on_hand_qty, available_qty,
                   reserved_qty, reorder_threshold, unit_cost, lead_time_hours
            FROM inventory_parts
            WHERE 1=1
        """
        params = []
        if category:
            params.append(category)
            query += f" AND category = ${len(params)}"
        if only_shortages:
            query += " AND available_qty <= reorder_threshold"
        query += " ORDER BY sku ASC"

        rows = await conn.fetch(query, *params)
        return [
            InventoryPartOut(
                id=r["id"],
                sku=r["sku"],
                name=r["name"],
                category=r["category"],
                physical_on_hand_qty=r["physical_on_hand_qty"],
                available_qty=r["available_qty"],
                reserved_qty=r["reserved_qty"],
                reorder_threshold=r["reorder_threshold"],
                unit_cost=r["unit_cost"],
                lead_time_hours=r["lead_time_hours"],
            )
            for r in rows
        ]

    @staticmethod
    async def reserve_parts(
        conn: asyncpg.Connection,
        request: ReservePartsRequest,
        actor_id: UUID
    ) -> ReservePartsResponse:
        """
        Atomically reserves parts for a work order.
        Sorts part IDs to prevent deadlocks (ORDER BY id ASC FOR UPDATE).
        Enforces 3-bucket conservation and triggers stock shortage cascade if stock is low.
        """
        wo_id = request.work_order_id

        # 1. Verify work order exists
        wo = await conn.fetchrow(
            """
            SELECT id, state, department_id, estimated_cost
            FROM work_orders
            WHERE id = $1
            FOR UPDATE;
            """,
            wo_id
        )
        if not wo:
            raise ResourceNotFoundError("Work Order", wo_id)

        # 2. Multi-part locking: Sort requested parts by part_id
        sorted_items = sorted(request.items, key=lambda x: str(x.part_id))
        part_ids = [item.part_id for item in sorted_items]

        # Fetch and lock rows in sorted order
        rows = await conn.fetch(
            """
            SELECT id, sku, name, physical_on_hand_qty, available_qty, reserved_qty, unit_cost, lead_time_hours
            FROM inventory_parts
            WHERE id = ANY($1::uuid[])
            ORDER BY id ASC
            FOR UPDATE;
            """,
            part_ids
        )
        parts_by_id = {r["id"]: r for r in rows}

        for item in sorted_items:
            if item.part_id not in parts_by_id:
                raise ResourceNotFoundError("Inventory Part", item.part_id)

        # 3. Check availability for all parts
        has_shortage = False
        shortage_reasons = []
        reservation_results = []
        total_additional_cost = Decimal("0.00")

        for item in sorted_items:
            part = parts_by_id[item.part_id]
            req_qty = item.requested_qty
            avail_qty = part["available_qty"]
            unit_cost = part["unit_cost"]

            if avail_qty < req_qty:
                has_shortage = True
                shortage_reasons.append(
                    f"{part['sku']} ({part['name']}): requested {req_qty}, available {avail_qty}"
                )
                reservation_results.append(
                    PartReservationResult(
                        part_id=item.part_id,
                        sku=part["sku"],
                        requested_qty=req_qty,
                        status="SHORTAGE_BLOCKED",
                        unit_cost=unit_cost
                    )
                )
            else:
                total_additional_cost += unit_cost * req_qty
                reservation_results.append(
                    PartReservationResult(
                        part_id=item.part_id,
                        sku=part["sku"],
                        requested_qty=req_qty,
                        status="RESERVED",
                        unit_cost=unit_cost
                    )
                )

        # 4. Handle Shortage Cascade vs Successful Reservation
        new_wo_state = wo["state"]

        if has_shortage:
            # Stock Shortage Cascade:
            # Record SHORTAGE_BLOCKED reservations
            for res in reservation_results:
                await conn.execute(
                    """
                    INSERT INTO part_reservations (work_order_id, part_id, requested_qty, locked_unit_cost, status)
                    VALUES ($1, $2, $3, $4, $5)
                    ON CONFLICT (work_order_id, part_id)
                    DO UPDATE SET requested_qty = EXCLUDED.requested_qty,
                                  locked_unit_cost = EXCLUDED.locked_unit_cost,
                                  status = EXCLUDED.status;
                    """,
                    wo_id,
                    res.part_id,
                    res.requested_qty,
                    res.unit_cost,
                    res.status
                )

            # Atomically update work order state to BLOCKED_PARTS & pause SLA
            blocked_msg = "Parts shortage: " + "; ".join(shortage_reasons)
            await conn.execute(
                """
                UPDATE work_orders
                SET state = 'BLOCKED_PARTS',
                    sla_is_paused = TRUE,
                    blocked_reason = $2,
                    updated_at = NOW()
                WHERE id = $1;
                """,
                wo_id,
                blocked_msg
            )
            new_wo_state = "BLOCKED_PARTS"

            # Create an EMERGENCY_PURCHASE approval entry with snapshot hash
            missing_parts_cost = sum(
                (r.unit_cost * r.requested_qty for r in reservation_results if r.status == "SHORTAGE_BLOCKED"),
                Decimal("0.00")
            )
            canonical_hash = await conn.fetchval(
                "SELECT fn_compute_canonical_wo_snapshot($1::uuid);", wo_id
            )
            await conn.execute(
                """
                INSERT INTO approvals (
                    work_order_id, approval_type, requested_by_user_id,
                    requested_amount, snapshot_hash, status
                )
                VALUES ($1, 'EMERGENCY_PURCHASE', $2, $3, $4, 'PENDING');
                """,
                wo_id,
                actor_id,
                missing_parts_cost,
                canonical_hash
            )

            # Audit record
            await conn.execute(
                """
                INSERT INTO audit_logs (work_order_id, actor_user_id, action, previous_state, new_state, details)
                VALUES ($1, $2, 'PARTS_SHORTAGE_BLOCKED', $3, 'BLOCKED_PARTS', $4::jsonb);
                """,
                wo_id,
                actor_id,
                wo["state"],
                f'{{"reason": "{blocked_msg}"}}'
            )

            return ReservePartsResponse(
                work_order_id=wo_id,
                all_reserved=False,
                work_order_state="BLOCKED_PARTS",
                reservations=reservation_results
            )

        else:
            # All parts available! Perform atomic reservation & 3-bucket movement
            for item in sorted_items:
                part = parts_by_id[item.part_id]
                req_qty = item.requested_qty

                # Insert ledger movement: delta_physical=0, delta_available=-N, delta_reserved=+N
                await conn.execute(
                    """
                    INSERT INTO inventory_movements (
                        part_id, work_order_id, actor_id, movement_type,
                        delta_physical, delta_available, delta_reserved
                    )
                    VALUES ($1, $2, $3, 'RESERVE', 0, $4, $5);
                    """,
                    item.part_id,
                    wo_id,
                    actor_id,
                    -req_qty,
                    req_qty
                )

                # Update balance on inventory_parts
                await conn.execute(
                    """
                    UPDATE inventory_parts
                    SET available_qty = available_qty - $2,
                        reserved_qty = reserved_qty + $2
                    WHERE id = $1;
                    """,
                    item.part_id,
                    req_qty
                )

                # Record part reservation
                await conn.execute(
                    """
                    INSERT INTO part_reservations (work_order_id, part_id, requested_qty, locked_unit_cost, status)
                    VALUES ($1, $2, $3, $4, 'RESERVED')
                    ON CONFLICT (work_order_id, part_id)
                    DO UPDATE SET requested_qty = EXCLUDED.requested_qty,
                                  locked_unit_cost = EXCLUDED.locked_unit_cost,
                                  status = 'RESERVED';
                    """,
                    wo_id,
                    item.part_id,
                    req_qty,
                    part["unit_cost"]
                )

            # Update work order estimated cost
            await conn.execute(
                """
                UPDATE work_orders
                SET estimated_cost = estimated_cost + $2,
                    updated_at = NOW()
                WHERE id = $1;
                """,
                wo_id,
                total_additional_cost
            )

            # Audit record
            await conn.execute(
                """
                INSERT INTO audit_logs (work_order_id, actor_user_id, action, previous_state, new_state, details)
                VALUES ($1, $2, 'PARTS_RESERVED', $3, $3, $4::jsonb);
                """,
                wo_id,
                actor_id,
                wo["state"],
                f'{{"parts_count": {len(sorted_items)}, "added_cost": {float(total_additional_cost)}}}'
            )

            return ReservePartsResponse(
                work_order_id=wo_id,
                all_reserved=True,
                work_order_state=wo["state"],
                reservations=reservation_results
            )

    @staticmethod
    async def receive_stock(
        conn: asyncpg.Connection,
        request: ReceiveStockRequest,
        actor_id: UUID
    ) -> List[InventoryPartOut]:
        """
        Receives new inventory stock.
        Atomically records 'RECEIPT' movement ledger entries and updates available & physical balances.
        """
        updated_parts = []
        sorted_items = sorted(request.items, key=lambda x: str(x.part_id))

        for item in sorted_items:
            part = await conn.fetchrow(
                """
                SELECT id, sku, name, category, physical_on_hand_qty, available_qty, reserved_qty, reorder_threshold, unit_cost, lead_time_hours
                FROM inventory_parts
                WHERE id = $1
                FOR UPDATE;
                """,
                item.part_id
            )
            if not part:
                raise ResourceNotFoundError("Inventory Part", item.part_id)

            qty = item.quantity
            new_cost = item.unit_cost if item.unit_cost is not None else part["unit_cost"]

            # 1. Insert movement record
            await conn.execute(
                """
                INSERT INTO inventory_movements (
                    part_id, actor_id, movement_type, delta_physical, delta_available, delta_reserved
                )
                VALUES ($1, $2, 'RECEIPT', $3, $3, 0);
                """,
                item.part_id,
                actor_id,
                qty
            )

            # 2. Update balances
            await conn.execute(
                """
                UPDATE inventory_parts
                SET physical_on_hand_qty = physical_on_hand_qty + $2,
                    available_qty = available_qty + $2,
                    unit_cost = $3
                WHERE id = $1;
                """,
                item.part_id,
                qty,
                new_cost
            )

            updated = await conn.fetchrow(
                """
                SELECT id, sku, name, category, physical_on_hand_qty, available_qty, reserved_qty, reorder_threshold, unit_cost, lead_time_hours
                FROM inventory_parts
                WHERE id = $1;
                """,
                item.part_id
            )
            updated_parts.append(
                InventoryPartOut(
                    id=updated["id"],
                    sku=updated["sku"],
                    name=updated["name"],
                    category=updated["category"],
                    physical_on_hand_qty=updated["physical_on_hand_qty"],
                    available_qty=updated["available_qty"],
                    reserved_qty=updated["reserved_qty"],
                    reorder_threshold=updated["reorder_threshold"],
                    unit_cost=updated["unit_cost"],
                    lead_time_hours=updated["lead_time_hours"],
                )
            )

        return updated_parts

    @staticmethod
    async def create_part(conn: asyncpg.Connection, req: CreatePartRequest, actor_id: UUID) -> InventoryPartOut:
        # Check if SKU already exists
        existing = await conn.fetchval(
            "SELECT id FROM inventory_parts WHERE sku = $1;", req.sku.strip().upper()
        )
        if existing:
            raise ConflictError(f"Part with SKU '{req.sku}' is already registered.")

        # Insert part into inventory_parts
        # Constraint: physical_on_hand_qty = available_qty + reserved_qty
        row = await conn.fetchrow(
            """
            INSERT INTO inventory_parts (
                sku, name, category, physical_on_hand_qty, available_qty, reserved_qty,
                reorder_threshold, unit_cost, lead_time_hours
            )
            VALUES ($1, $2, $3::issue_category, $4, $4, 0, $5, $6, $7)
            RETURNING id, sku, name, category, physical_on_hand_qty, available_qty, reserved_qty, reorder_threshold, unit_cost, lead_time_hours;
            """,
            req.sku.strip().upper(),
            req.name.strip(),
            req.category.strip().upper(),
            req.quantity,
            req.reorder_threshold,
            req.unit_cost,
            req.lead_time_hours
        )

        # Record receipt movement for initial balance
        if req.quantity > 0:
            await conn.execute(
                """
                INSERT INTO inventory_movements (part_id, actor_id, movement_type, delta_physical, delta_available, delta_reserved)
                VALUES ($1, $2, 'RECEIPT', $3, $3, 0);
                """,
                row["id"], actor_id, req.quantity
            )

        return InventoryPartOut(
            id=row["id"],
            sku=row["sku"],
            name=row["name"],
            category=row["category"],
            physical_on_hand_qty=row["physical_on_hand_qty"],
            available_qty=row["available_qty"],
            reserved_qty=row["reserved_qty"],
            reorder_threshold=row["reorder_threshold"],
            unit_cost=row["unit_cost"],
            lead_time_hours=row["lead_time_hours"],
        )

    @staticmethod
    async def delete_part(conn: asyncpg.Connection, part_id: UUID):
        existing = await conn.fetchrow("SELECT sku FROM inventory_parts WHERE id = $1;", part_id)
        if not existing:
            raise ResourceNotFoundError("InventoryPart", str(part_id))

        res_count = await conn.fetchval(
            "SELECT COUNT(*) FROM part_reservations WHERE part_id = $1 AND status = 'RESERVED';",
            part_id
        )
        if res_count > 0:
            raise ConflictError(f"Cannot delete part '{existing['sku']}': {res_count} active reservation(s) exist.")

        await conn.execute("DELETE FROM inventory_movements WHERE part_id = $1;", part_id)
        await conn.execute("DELETE FROM inventory_parts WHERE id = $1;", part_id)

