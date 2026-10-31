# CampusOps Digital Twin — Backend Contract (Local-Meter Campus)

The backend specification is authoritative for IDs, operational records, status vocabularies, permissions, state transitions, bookings, inventory, and approvals. This map contract replaces GeoJSON geometry with campus-local coordinates. The scene is an illustrative navigation model, not a survey-accurate digital twin.

## `GET /api/v1/campus/map-status`

The API returns `campusId`, `campusName`, `generatedAt`, `nodes`, `dependencies`, `bookings`, `parts`, `incidents`, and `whatIf` as described by the existing contract. Geometry-related node fields are now local-meter fields:

- Building nodes: `position: { x, z }`, `footprint: { width, depth }`, `rotation` in radians, `heightMeters`, and `floorCount`.
- Room nodes: `position: { x, z }` within their parent building, plus `floor` and `capacity`.
- Non-spatial nodes may use null `position` and `footprint`.
- Equipment may include an approximate room-local `position`; if absent, procedural placement is used.

```json
{
  "id": "building-pg",
  "parentId": null,
  "nodeType": "BUILDING",
  "name": "PG Block",
  "domain": null,
  "status": "incident",
  "position": { "x": 5, "z": -8 },
  "footprint": { "width": 22, "depth": 18 },
  "rotation": 0,
  "heightMeters": 16,
  "floorCount": 4,
  "floor": null,
  "capacity": null,
  "equipment": []
}
```

```json
{
  "id": "room-a101",
  "parentId": "building-pg",
  "nodeType": "ROOM",
  "name": "A101",
  "domain": null,
  "status": "incident",
  "position": { "x": -4, "z": 2 },
  "footprint": null,
  "rotation": null,
  "heightMeters": null,
  "floorCount": null,
  "floor": 1,
  "capacity": 60,
  "equipment": []
}
```

The API does not need to return decorative roads, paths, courts, trees, lighting, or building facade detail. The frontend generates these from campus configuration. Building and room IDs remain stable, including `building-main`, `building-pg`, `building-civil`, `building-electronics`, `building-mechanical`, `room-a101`, and `room-b204`.

## Operations and What-If

Incident `affectedNodeIds`, parent/child incident links, work-order states (`OPEN`, `ASSIGNED`, `IN_PROGRESS`, `COMPLETED`, `BLOCKED`), assignment explanation, staff display names, `allowedActions`, bookings, parts, and invariants retain their previous contract. The dependency graph still uses `campus_nodes` and `node_dependencies` with `POWER`, `NETWORK`, `WATER`, and `HVAC` domains. All value-to-visual mapping stays in `src/adapters/campusMapAdapter.ts`.

Simulation remains a read-only Plan A/Plan B overlay with `basedOnGeneratedAt`; simulate, approve, execute and the idempotency key/409 behavior keep their previously proposed paths and shapes pending backend confirmation. Scenario buttons call the backend through the same mock/real API adapter.

## Illustrative building mapping

| Stable ID | Display name | Concept image reference |
| --- | --- | --- |
| `building-main` | Main Block | Academic Block III — CSE/EEE |
| `building-pg` | PG Block | Academic Block IV — PG Studies |
| `building-civil` | Civil Block | Academic Block II — Civil/Mech |
| `building-mechanical` | Mechanical Block | Academic Block II — Civil/Mech; split into two illustrative wings |
| `building-electronics` | Electronics Block | Workshops/electronics area; approximate placement |
| `landmark-hostel` | Boys Hostel | Boys Hostel callout |
| `landmark-canteen` | Canteen | Canteen callout |
| `landmark-tnp` | TNP Entrance | TNP venue entrance callout |
| `landmark-library` | Library | Library callout |
| `landmark-auditorium` | Auditorium | Auditorium callout |

The concept images contain stylized/uncertain labels and do not establish footprints or verified building relationships. These mappings are for the demo scene only; backend node IDs remain unchanged.
