from typing import List, Dict, Any, Optional
from uuid import UUID
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, status
from app.core.security import get_current_user, CurrentUser, require_roles
from app.database import acquire_db_connection

class RoomRegisterRequest(BaseModel):
    node_code: str = Field(..., description="Unique code for the room e.g. RM-ACAD-305")
    name: str = Field(..., description="Human readable room name e.g. Smart Classroom 305")
    room_capacity: int = Field(0, ge=0, le=5000, description="Seating capacity (0 for administrative/not applicable)")
    room_type: str = Field("CLASSROOM", description="Type of room e.g. CLASSROOM, LAB, ADMINISTRATIVE, AUDITORIUM, FOOD_COURT, SEMINAR_HALL, WORKSHOP")
    building_code: str = Field(..., description="Building block code e.g. EEC-ACAD")
    floor_number: int = Field(1, ge=0, le=10, description="Floor number")
    room_features: List[str] = Field(default_factory=list, description="List of room features/tags")
    is_operational: bool = True
    criticality_weight: int = Field(10, ge=1, le=30)

class RoomUpdateRequest(BaseModel):
    name: Optional[str] = None
    room_capacity: Optional[int] = None
    room_type: Optional[str] = None
    floor_number: Optional[int] = None
    room_features: Optional[List[str]] = None
    is_operational: Optional[bool] = None

router = APIRouter(prefix="/campus", tags=["Campus Digital Twin & Topology"])

CAMPUS_BLOCKS = [
    {
        "building_code": "EEC-MAIN",
        "name": "Main Administrative Block",
        "floors": 4,
        "height_m": 14.0,
        "center": [80.18055, 13.03305]
    },
    {
        "building_code": "EEC-ACAD",
        "name": "Academic Tech Block (CSE/IT/AI&DS/ECE)",
        "floors": 5,
        "height_m": 17.5,
        "center": [80.18165, 13.03285]
    },
    {
        "building_code": "EEC-MECH-PG",
        "name": "Mechanical, Civil & Central PG Library Block",
        "floors": 4,
        "height_m": 14.0,
        "center": [80.18050, 13.03195]
    },
    {
        "building_code": "EEC-ROBOTICS",
        "name": "ABB Robotics Research & Automation Centre",
        "floors": 2,
        "height_m": 7.0,
        "center": [80.18180, 13.03195]
    },
    {
        "building_code": "EEC-AUD-FC",
        "name": "TRP Auditorium & Central Food Court",
        "floors": 2,
        "height_m": 8.0,
        "center": [80.18115, 13.03120]
    }
]


@router.get("/map-status")
async def get_campus_map_status(current_user: CurrentUser = Depends(get_current_user)):
    """
    Returns real-time 2.5D extrusion color and operational metrics for all 5 SRM Easwari blocks.
    Colors:
      - #ef4444 (Critical / P0 Disruption)
      - #f97316 (Blocked on Parts)
      - #eab308 (Active Maintenance / Non-operational room)
      - #3b82f6 (Normal Operational)
    """
    async with acquire_db_connection(
        actor_id=current_user.id,
        actor_role=current_user.role,
        dept_id=current_user.department_id,
    ) as conn:
        block_statuses = []

        for b in CAMPUS_BLOCKS:
            b_code = b["building_code"]

            # Query active work orders in this block
            wo_stats = await conn.fetchrow(
                """
                SELECT 
                    COUNT(*) AS active_tickets,
                    COUNT(*) FILTER (WHERE calculated_priority = 'P0_CRITICAL') AS critical_tickets,
                    COUNT(*) FILTER (WHERE state = 'BLOCKED_PARTS') AS blocked_parts_tickets,
                    COUNT(*) FILTER (WHERE state IN ('ASSIGNED', 'IN_PROGRESS')) AS in_progress_tickets
                FROM work_orders wo
                JOIN campus_nodes cn ON cn.id = wo.target_node_id
                WHERE cn.building_code = $1
                  AND wo.state NOT IN ('RESOLVED', 'CLOSED', 'MERGED_DUPLICATE');
                """,
                b_code
            )

            # Query non-operational rooms
            non_op_count = await conn.fetchval(
                """
                SELECT COUNT(*) FROM campus_nodes
                WHERE building_code = $1 AND is_operational = FALSE;
                """,
                b_code
            ) or 0

            active_t = wo_stats["active_tickets"] if wo_stats else 0
            crit_t = wo_stats["critical_tickets"] if wo_stats else 0
            blocked_t = wo_stats["blocked_parts_tickets"] if wo_stats else 0
            in_prog_t = wo_stats["in_progress_tickets"] if wo_stats else 0

            if crit_t > 0:
                color = "#ef4444"
                status_label = "CRITICAL_DISRUPTION"
            elif blocked_t > 0:
                color = "#f97316"
                status_label = "PARTS_SHORTAGE"
            elif non_op_count > 0 or in_prog_t > 0:
                color = "#eab308"
                status_label = "MAINTENANCE_ACTIVE"
            else:
                color = "#3b82f6"
                status_label = "OPERATIONAL"

            block_statuses.append({
                "building_code": b_code,
                "name": b["name"],
                "floors": b["floors"],
                "height_m": b["height_m"],
                "center": b["center"],
                "color": color,
                "status_label": status_label,
                "active_work_orders": active_t,
                "critical_work_orders": crit_t,
                "blocked_parts_work_orders": blocked_t,
                "non_operational_nodes": non_op_count
            })

        return {
            "campus_name": "SRM Easwari Engineering College",
            "viewport": {
                "center": [80.1810, 13.0324],
                "zoom": 17.2,
                "pitch": 58,
                "bearing": -22
            },
            "blocks": block_statuses
        }


@router.get("/blocks/{block_code}")
async def get_block_details(
    block_code: str,
    current_user: CurrentUser = Depends(get_current_user)
):
    """Returns granular building inspector details: rooms, assets, and active work orders."""
    async with acquire_db_connection(
        actor_id=current_user.id,
        actor_role=current_user.role,
        dept_id=current_user.department_id,
    ) as conn:
        nodes = await conn.fetch(
            """
            SELECT id, node_code, name, node_type, floor_number, room_capacity,
                   room_features, is_operational, criticality_weight
            FROM campus_nodes
            WHERE building_code = $1
            ORDER BY floor_number ASC, node_code ASC;
            """,
            block_code
        )

        work_orders = await conn.fetch(
            """
            SELECT wo.id, wo.ticket_number, cn.node_code, wo.category, wo.state,
                   wo.calculated_priority, wo.raw_description, wo.created_at
            FROM work_orders wo
            JOIN campus_nodes cn ON cn.id = wo.target_node_id
            WHERE cn.building_code = $1
              AND wo.state NOT IN ('RESOLVED', 'CLOSED', 'MERGED_DUPLICATE')
            ORDER BY wo.created_at DESC;
            """,
            block_code
        )

        b_meta = next((b for b in CAMPUS_BLOCKS if b["building_code"] == block_code), None)

        return {
            "building_code": block_code,
            "metadata": b_meta or {"name": block_code, "floors": 4, "height_m": 14.0},
            "nodes": [dict(n) for n in nodes],
            "active_work_orders": [dict(w) for w in work_orders]
        }


@router.get("/nodes")
async def list_campus_nodes(
    building_code: Optional[str] = None,
    node_type: Optional[str] = None,
    current_user: CurrentUser = Depends(get_current_user)
):
    """Lists all campus nodes with optional building and node_type filter."""
    async with acquire_db_connection(
        actor_id=current_user.id,
        actor_role=current_user.role,
        dept_id=current_user.department_id,
    ) as conn:
        rows = await conn.fetch(
            """
            SELECT id, node_code, name, node_type, building_code, floor_number,
                   room_capacity, room_features, is_operational, criticality_weight
            FROM campus_nodes
            WHERE ($1::text IS NULL OR building_code = $1)
              AND ($2::text IS NULL OR node_type = $2)
            ORDER BY building_code ASC, node_code ASC;
            """,
            building_code,
            node_type
        )
        return [dict(r) for r in rows]


@router.get("/graph")
async def get_campus_graph(current_user: CurrentUser = Depends(get_current_user)):
    """
    Returns nodes and edges formatted for React Flow (@xyflow/react) Consequence Graph.
    Shows the live causal cascade: Fault -> Room Lock -> Exam Clash -> Contingency Hold -> Part Shortage.
    """
    async with acquire_db_connection(
        actor_id=current_user.id,
        actor_role=current_user.role,
        dept_id=current_user.department_id,
    ) as conn:
        # 1. Fetch campus nodes (focusing on infrastructure and active rooms)
        nodes_raw = await conn.fetch(
            """
            SELECT id, node_code, name, node_type, building_code, floor_number, is_operational
            FROM campus_nodes
            WHERE node_type IN ('ELECTRICAL_PANEL', 'NETWORK_SWITCH', 'HVAC_AHU')
               OR is_operational = FALSE
               OR id IN (SELECT target_node_id FROM work_orders WHERE state NOT IN ('RESOLVED', 'CLOSED', 'MERGED_DUPLICATE'))
               OR id IN (SELECT room_node_id FROM room_bookings WHERE status IN ('CONFIRMED', 'CONTINGENCY_HOLD'))
            LIMIT 50;
            """
        )

        # 2. Fetch DAG dependencies
        deps_raw = await conn.fetch(
            """
            SELECT parent_node_id, child_node_id, dependency_domain
            FROM node_dependencies;
            """
        )

        # 3. Fetch active work orders for causal chain
        wo_raw = await conn.fetch(
            """
            SELECT id, ticket_number, target_node_id, category, state, calculated_priority, raw_description
            FROM work_orders
            WHERE state NOT IN ('RESOLVED', 'CLOSED', 'MERGED_DUPLICATE')
            LIMIT 20;
            """
        )

        flow_nodes = []
        flow_edges = []

        # Position helpers
        x_coords = {"ELECTRICAL_PANEL": 100, "NETWORK_SWITCH": 350, "ROOM": 600, "EQUIPMENT": 850}
        y_offset = 50

        node_id_set = set()

        for idx, n in enumerate(nodes_raw):
            n_id = str(n["id"])
            node_id_set.add(n_id)
            n_type = n["node_type"]
            x = x_coords.get(n_type, 400)
            y = (idx % 10) * 120 + 50

            flow_nodes.append({
                "id": n_id,
                "type": "campusNode",
                "position": {"x": x, "y": y},
                "data": {
                    "node_code": n["node_code"],
                    "name": n["name"],
                    "node_type": n["node_type"],
                    "building_code": n["building_code"],
                    "is_operational": n["is_operational"],
                    "status": "OPERATIONAL" if n["is_operational"] else "DISRUPTED"
                }
            })

        for edge in deps_raw:
            p_id = str(edge["parent_node_id"])
            c_id = str(edge["child_node_id"])
            if p_id in node_id_set and c_id in node_id_set:
                flow_edges.append({
                    "id": f"e-{p_id}-{c_id}",
                    "source": p_id,
                    "target": c_id,
                    "label": edge["dependency_domain"],
                    "animated": True,
                    "style": {"stroke": "#60a5fa", "strokeWidth": 2}
                })

        # Add active incident nodes
        for idx, wo in enumerate(wo_raw):
            wo_id = str(wo["id"])
            target_id = str(wo["target_node_id"]) if wo["target_node_id"] else None
            flow_nodes.append({
                "id": f"wo-{wo_id}",
                "type": "incidentNode",
                "position": {"x": 850, "y": idx * 130 + 50},
                "data": {
                    "ticket_number": wo["ticket_number"],
                    "category": wo["category"],
                    "state": wo["state"],
                    "priority": wo["calculated_priority"],
                    "description": wo["raw_description"][:60] + "..."
                }
            })

            if target_id and target_id in node_id_set:
                flow_edges.append({
                    "id": f"e-wo-{wo_id}-{target_id}",
                    "source": target_id,
                    "target": f"wo-{wo_id}",
                    "label": f"Incident #{wo['ticket_number']}",
                    "animated": True,
                    "style": {"stroke": "#ef4444" if wo["calculated_priority"] == "P0_CRITICAL" else "#f97316", "strokeWidth": 2}
                })

        return {
            "nodes": flow_nodes,
            "edges": flow_edges
        }


@router.get("/rooms")
async def list_registered_rooms(
    building_code: Optional[str] = None,
    current_user: CurrentUser = Depends(get_current_user)
):
    """
    Returns all registered rooms with their capacity, room type, features, and operational status.
    """
    async with acquire_db_connection(
        actor_id=current_user.id,
        actor_role=current_user.role,
        dept_id=current_user.department_id,
    ) as conn:
        query = """
            SELECT 
                id, node_code, name, building_code, floor_number, 
                room_capacity, COALESCE(room_type, 'CLASSROOM') AS room_type,
                room_features, is_operational, criticality_weight
            FROM campus_nodes
            WHERE node_type = 'ROOM'
        """
        params = []
        if building_code:
            query += " AND building_code = $1"
            params.append(building_code)
        
        query += " ORDER BY building_code ASC, floor_number ASC, node_code ASC;"
        rows = await conn.fetch(query, *params)
        
        return [
            {
                "id": str(r["id"]),
                "node_code": r["node_code"],
                "name": r["name"],
                "building_code": r["building_code"],
                "floor_number": r["floor_number"],
                "room_capacity": r["room_capacity"],
                "room_type": r["room_type"],
                "room_features": list(r["room_features"] or []),
                "is_operational": r["is_operational"],
                "criticality_weight": r["criticality_weight"]
            }
            for r in rows
        ]


@router.post("/rooms", status_code=status.HTTP_201_CREATED)
async def register_room(
    req: RoomRegisterRequest,
    current_user: CurrentUser = Depends(require_roles(["SYS_ADMIN", "FACILITIES_ADMIN", "DEPT_MANAGER", "TIMETABLE_COORD"]))
):
    """
    Registers a new room in the campus infrastructure topology.
    Requires administrative or managerial authorization.
    """
    async with acquire_db_connection(
        actor_id=current_user.id,
        actor_role=current_user.role,
        dept_id=current_user.department_id,
    ) as conn:
        # Check for unique node code
        existing = await conn.fetchval(
            "SELECT id FROM campus_nodes WHERE node_code = $1;", req.node_code
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Room with code '{req.node_code}' is already registered."
            )

        row = await conn.fetchrow(
            """
            INSERT INTO campus_nodes (
                node_code, name, node_type, building_code, floor_number,
                room_capacity, room_type, room_features, is_operational, criticality_weight
            )
            VALUES ($1, $2, 'ROOM', $3, $4, $5, $6, $7, $8, $9)
            RETURNING id, node_code, name, building_code, floor_number, room_capacity, room_type, room_features, is_operational, criticality_weight;
            """,
            req.node_code.strip().upper(),
            req.name.strip(),
            req.building_code.strip().upper(),
            req.floor_number,
            req.room_capacity,
            req.room_type.strip().upper(),
            req.room_features,
            req.is_operational,
            req.criticality_weight
        )

        return {
            "id": str(row["id"]),
            "node_code": row["node_code"],
            "name": row["name"],
            "building_code": row["building_code"],
            "floor_number": row["floor_number"],
            "room_capacity": row["room_capacity"],
            "room_type": row["room_type"],
            "room_features": list(row["room_features"] or []),
            "is_operational": row["is_operational"],
            "criticality_weight": row["criticality_weight"],
            "message": f"Room '{row['node_code']}' registered successfully."
        }


@router.patch("/rooms/{room_id}")
async def update_room(
    room_id: UUID,
    req: RoomUpdateRequest,
    current_user: CurrentUser = Depends(require_roles(["SYS_ADMIN", "FACILITIES_ADMIN", "DEPT_MANAGER", "TIMETABLE_COORD"]))
):
    """
    Updates room details, operational status, capacity, or features.
    """
    async with acquire_db_connection(
        actor_id=current_user.id,
        actor_role=current_user.role,
        dept_id=current_user.department_id,
    ) as conn:
        existing = await conn.fetchrow(
            "SELECT * FROM campus_nodes WHERE id = $1 AND node_type = 'ROOM';", room_id
        )
        if not existing:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found.")

        new_name = req.name if req.name is not None else existing["name"]
        new_capacity = req.room_capacity if req.room_capacity is not None else existing["room_capacity"]
        new_type = req.room_type if req.room_type is not None else existing.get("room_type", "CLASSROOM")
        new_floor = req.floor_number if req.floor_number is not None else existing["floor_number"]
        new_features = req.room_features if req.room_features is not None else existing["room_features"]
        new_operational = req.is_operational if req.is_operational is not None else existing["is_operational"]

        row = await conn.fetchrow(
            """
            UPDATE campus_nodes
            SET name = $2,
                room_capacity = $3,
                room_type = $4,
                floor_number = $5,
                room_features = $6,
                is_operational = $7
            WHERE id = $1
            RETURNING id, node_code, name, building_code, floor_number, room_capacity, room_type, room_features, is_operational, criticality_weight;
            """,
            room_id, new_name, new_capacity, new_type, new_floor, new_features, new_operational
        )

        return {
            "id": str(row["id"]),
            "node_code": row["node_code"],
            "name": row["name"],
            "building_code": row["building_code"],
            "floor_number": row["floor_number"],
            "room_capacity": row["room_capacity"],
            "room_type": row["room_type"],
            "room_features": list(row["room_features"] or []),
            "is_operational": row["is_operational"],
            "criticality_weight": row["criticality_weight"],
            "message": f"Room '{row['node_code']}' updated successfully."
        }


@router.delete("/rooms/{room_id}")
async def delete_room(
    room_id: UUID,
    current_user: CurrentUser = Depends(require_roles(["SYS_ADMIN", "FACILITIES_ADMIN"]))
):
    """
    Decommission and remove a room from the campus registry.
    """
    async with acquire_db_connection(
        actor_id=current_user.id,
        actor_role=current_user.role,
        dept_id=current_user.department_id,
    ) as conn:
        existing = await conn.fetchrow(
            "SELECT node_code FROM campus_nodes WHERE id = $1 AND node_type = 'ROOM';", room_id
        )
        if not existing:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found.")

        # Check for active bookings
        active_bookings = await conn.fetchval(
            "SELECT COUNT(*) FROM room_bookings WHERE room_node_id = $1 AND status IN ('CONFIRMED', 'IN_PROGRESS', 'CONTINGENCY_HOLD');",
            room_id
        )
        if active_bookings > 0:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Cannot delete room '{existing['node_code']}': {active_bookings} active booking(s) exist."
            )

        await conn.execute("DELETE FROM campus_nodes WHERE id = $1;", room_id)
        return {"success": True, "message": f"Room '{existing['node_code']}' deleted successfully."}


