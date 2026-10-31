# SRM Easwari Engineering College — Campus Registry & Naming Specification

## 1. Single Source of Truth
`src/data/registry/campusRegistry.json` is the sole authoritative registry for campus spaces and assets.
All subsystems (3D scene, cutaway view, operations panel, external databases, APIs) derive identifiers and metadata from this file.

---

## 2. Identifier Syntax
- **Character Set:** Strict ASCII: uppercase letters `A–Z`, digits `0–9`, and hyphens `-`.
- **Database Safety:** Firestore, BigQuery, and REST safe (no slashes, spaces, or URI-escaped characters).
- **Immutability:** Once assigned, an ID is never reassigned or deleted. If renamed, the previous identifier must be appended to `aliases[]`.

---

## 3. Hierarchy & Formats

### 3.1 Block Identifiers (`blockId`)
One canonical short code per recognized campus block:

| `blockId` | Campus Block | OSM Way ID | Node ID | Source |
|---|---|---:|---|---|
| `PG` | PG Block | 355636688 | `building-pg` | AICTE / Brochure |
| `MAIN` | Main Block | 355617963 | `building-main` | AICTE / Brochure |
| `CIVIL` | Civil Block | 355636704 | `building-civil` | AICTE / Brochure |
| `ECE` | Electronics Block | 355636432 | `building-electronics` | AICTE / Brochure |
| `MECH` | Mechanical Block | 355636701 | `building-mechanical` | AICTE / Brochure |
| `HOSTEL` | Boys Hostel | 768032824 | `landmark-hostel` | Handbook / OSM |
| `CANTEEN` | Canteen | 355636593 | `landmark-canteen` | Handbook / OSM |
| `LIB` | Central Library | 355636605 | `landmark-library` | Handbook / OSM |
| `AUD` | TRP Auditorium | 355636577 | `landmark-auditorium` | Handbook / OSM |
| `TNP` | TNP Venue | 355636490 | `landmark-tnp` | Handbook / OSM |
| `BLK4` - `BLK12` | Numbered Blocks 4 to 12 | 354774621, etc. | `building-block-4`..`12` | Provisional |

### 3.2 Floor Identifiers (`floorId`)
Format: `<BLOCK>-F<FLOOR_NUMBER>`  
Ground floor is floor `0`.
Examples:
- `PG-F0`: PG Block Ground Floor
- `PG-F1`: PG Block First Floor
- `MAIN-F2`: Main Block Second Floor

### 3.3 Room Identifiers (`roomId`)
Format: `<BLOCK>-<FLOOR><NN>`
- Ground floor (`0`): `<BLOCK>-001`, `<BLOCK>-002`, ...
- 1st floor (`1`): `<BLOCK>-101`, `<BLOCK>-102`, ...
- 2nd floor (`2`): `<BLOCK>-201`, `<BLOCK>-202`, ...
- The room's functional type is stored in the `type` attribute (`classroom` | `lecture_hall` | `smart_lab`), NOT in the ID.
- Display name format: `"<BLOCK> <FLOOR><NN>"`, e.g. `"PG 001"`, `"MAIN 204"`.

### 3.4 Equipment Identifiers (`equipmentId`)
Format: `<ROOMID>-<EQUIPMENT_CODE>`
Standard codes:
- `PROJ`: Ceiling-mounted multimedia projector
- `AC`: Air conditioning split system (indoor & outdoor unit)
- `TV`: Wall-mounted smart display / LED television

Examples:
- `PG-001-PROJ`
- `PG-001-AC`
- `PG-001-TV`

---

## 4. Legacy Compatibility & Aliasing
Existing legacy node IDs and aliases are maintained through the `aliases[]` and `nodeId` fields:
- `PG-001` has `nodeId: "room-a101"`, `aliases: ["A101", "room-a101"]`, `type: "smart_lab"`.
- `MAIN-204` has `nodeId: "room-b204"`, `aliases: ["B204", "room-b204"]`, `type: "lecture_hall"`.
- `PG-001-PROJ` has `aliases: ["projector-a101"]`.

All What-If simulation queries referencing `room-a101`, `room-b204`, or `projector-a101` resolve directly via these aliases.

