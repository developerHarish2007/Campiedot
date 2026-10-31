# OpenStreetMap footprint import and provisional name mapping

Snapshot: Overpass `osm_base` timestamp `2026-10-30T08:09:19Z`.

Campus boundary: [SRM Easwari College of Engineering, OSM way 32945542](https://www.openstreetmap.org/way/32945542). The source boundary is converted to local metres with origin `13.0335762, 80.17934165`; `x` points east and `z` points south.

## Footprints found

The boundary contains 18 mapped building footprints and 25 road/path ways. The Overpass bounding box also returned 79 nearby building ways outside the campus boundary; they are not rendered as campus buildings. One additional footprint, OSM way 768032824, is tagged `tourism=hostel` but sits just outside the campus boundary, so it is included as context for the existing Boys Hostel node.

None of the 18 in-boundary building ways has an OSM `name`, `height`, or `building:levels` tag. The hostel has the `tourism=hostel` tag but no height/floor tags. Procedural heights and floors are explicitly estimates from footprint size; they are not OSM facts.

## Existing CampusOps IDs mapped to OSM footprints

These are editable candidates, not verified building-name matches. OSM has no names to establish the associations; please correct the `osmWayId` values in `src/data/osmBuildingAssignments.ts` where needed. Node IDs remain unchanged.

| CampusOps node ID | Current label | OSM way | Confidence / basis |
|---|---|---:|---|
| `building-main` | Main Block | 355617963 | Low; largest south-west footprint |
| `building-pg` | PG Block | 355636688 | Low; large central footprint |
| `building-civil` | Civil Block | 355636704 | Low; large southern footprint |
| `building-electronics` | Electronics Block | 355636432 | Low; large eastern footprint |
| `building-mechanical` | Mechanical Block | 355636701 | Low; large south-eastern footprint |
| `landmark-hostel` | Boys Hostel | 768032824 | Medium; OSM explicitly tags this way `tourism=hostel`, outside boundary |
| `landmark-canteen` | Canteen | 355636593 | Low; small central footprint |
| `landmark-library` | Library | 355636605 | Low; medium central-west footprint |
| `landmark-auditorium` | Auditorium | 355636577 | Low; large north-eastern footprint |
| `landmark-tnp` | TNP Venue | 355636490 | Low; small south-west footprint |
| `building-block-4` | Block 4 | 354774621 | Provisional numbered block assignment |
| `building-block-5` | Block 5 | 355617971 | Provisional numbered block assignment |
| `building-block-6` | Block 6 | 355617978 | Provisional numbered block assignment |
| `building-block-7` | Block 7 | 355617990 | Provisional numbered block assignment |
| `building-block-8` | Block 8 | 355618012 | Provisional numbered block assignment |
| `building-block-9` | Block 9 | 355636470 | Provisional numbered block assignment |
| `building-block-10` | Block 10 | 355636693 | Provisional numbered block assignment |
| `building-block-11` | Block 11 | 355636694 | Provisional numbered block assignment |
| `building-block-12` | Block 12 | 364147634 | Provisional numbered block assignment |

## Numbered block assignments

All 9 previously unassigned in-boundary footprints are assigned sequential numbered block designations (Block 4 through Block 12) continuing after the primary named academic blocks:

- `354774621` → Block 4
- `355617971` → Block 5
- `355617978` → Block 6
- `355617990` → Block 7
- `355618012` → Block 8
- `355636470` → Block 9
- `355636693` → Block 10
- `355636694` → Block 11
- `364147634` → Block 12

## Public reference cross-check (2026-10-30)

The real map view shows a compact, dense Ramapuram campus shared by Easwari and neighboring SRM facilities. Google Maps labels visible around the campus include SRM Boys Hostel-3, SRM Dental College, SRM Prime Hospital, Ramapuram Management Studies, Architecture Block-2, and ECE Park. The SRM Easwari POI pin is near the south-west part of the mapped boundary; do not use that pin as the campus center.

The official 2025 brochure contains a labeled aerial view, but its callouts mix Easwari and neighboring SRMIST facilities: SRM Dental College, SRMIST Admin Block, PG Block, SRM Prime Hospital, Boys Hostel, Sports Complex, Block 5, and East Block. It is useful for orientation and broad landmark naming, but does not identify every OSM footprint one-to-one. The official handbook names seven academic blocks: Main Block, Electronics Block I, Electronics Block II, Civil Block, Basic Engineering Block, PG Block, and Mechanical Block. It also mentions workshop blocks, TRP Auditorium, canteens, and five residential hostels. The handbook has a count discrepancy: its opening text says three workshop blocks while its table lists two.

Public photos provide facade references for the Mechanical Block and TRP Auditorium, and the college hostel page includes a Boys' Hostel photo. These support architectural appearance, not georeferencing. The current assignments below remain candidates unless a label is visible on an aerial callout or a building-specific sign/photo can be tied to a footprint.

### Wider map context imported for the 3D scene

The app now loads a separate OSM extract for the neighborhood around the campus (bbox `80.1755,13.0300,80.1830,13.0370`, local origin `13.0335762,80.17934165`). It contains 682 surrounding building footprints, 154 road/path ways, Ramapuram Eri, and GCC Park, Ramapuram. Campus geometry remains from the original in-boundary extract. The renderer draws these as contextual masses and surfaces so the campus sits in its street grid rather than on a green plane.

Google Maps satellite imagery at zoom 18 shows the actual campus is a compact, dense cluster between Bharathi Salai and SRM BMS Block Road, with a large tree canopy around the curving internal drive, SRMIST buildings, Boys Hostel-3, Dental College and Prime Hospital immediately to the east, and dense residential streets to the south. This helped confirm the orientation and surrounding landmarks. Google imagery is only a visual cross-check; it is not copied into the app. Trees are not individually mapped in this OSM extract (`0` tagged tree nodes), so the limited roadside row is a visual approximation and must not be treated as surveyed tree positions.

OSM does not provide reliable height/floor tags for these neighboring buildings. The scene estimates context massing from footprint size (6.4 m default), and estimates campus-building heights where tags are missing. Footprint/street alignment is stronger than name, height, and vegetation accuracy. The model is not supportably “80% accurate” in every dimension. Building shape alignment can be checked against satellite imagery; exact identity, vegetation, and floor heights need a campus plan, field photos with locations, or manual confirmation.

The context extract is stored at `public/data/osm-surroundings.json` and was retrieved from the [OpenStreetMap map API](https://api.openstreetmap.org/api/0.6/map?bbox=80.1755,13.0300,80.1830,13.0370). The app footer credits OSM wherever the imported geometry is shown.

Sources:

- [Google Maps satellite view at the campus](https://www.google.com/maps/@13.0320501,80.1794075,18z/data=!3m1!1e3)
- [SRM Easwari Information Brochure 2025](https://srmeaswari.ac.in/wp-content/uploads/2024/12/Information-Brochure-2025.pdf)
- [SRM Easwari Academic Calendar / Handbook 2022-23](https://srmeaswari.ac.in/wp-content/uploads/2024/03/Academic-Calendar-2022-2023-2.pdf)
- [SRM Easwari Hostel page](https://srmeaswari.ac.in/hostel/)
- [Public campus photo gallery](https://www.shiksha.com/college/srm-easwari-engineering-college-ramapuram-chennai-1517/gallery)
- [Mechanical Block and TRP Auditorium reference photos](https://allegiance-educare.in/college/easwari-engineering-college-eec)

## Complete footprint index

Coordinates are local metres from the origin above (`x` east, `z` south). Labels in the final column are provisional candidate mappings; blank means no name match is supported yet.

| OSM way | Center x | Center z | Width × depth (m) | Candidate label |
|---:|---:|---:|---:|---|
| 354774621 | 220.65 | -64.03 | 16.88 × 19.16 | Block 4 (provisional) |
| 355617963 | -54.03 | 160.63 | 125.57 × 39.96 | Main Block (low confidence) |
| 355617971 | -205.00 | 144.52 | 44.16 × 16.62 | Block 5 (provisional) |
| 355617978 | -130.42 | 169.89 | 35.75 × 16.95 | Block 6 (provisional) |
| 355617990 | -145.72 | 149.74 | 45.11 × 21.84 | Block 7 (provisional) |
| 355618012 | -95.89 | 177.62 | 31.14 × 15.19 | Block 8 (provisional) |
| 355636432 | 226.76 | 12.93 | 42.43 × 77.41 | Electronics Block (low; I/II not distinguished) |
| 355636470 | 180.26 | 49.17 | 45.20 × 49.00 | Block 9 (provisional) |
| 355636490 | 64.61 | 117.87 | 23.09 × 21.30 | TNP Venue (low confidence) |
| 355636577 | 165.53 | -17.44 | 48.64 × 43.75 | Auditorium (low confidence) |
| 355636593 | 57.67 | 19.73 | 13.07 × 17.79 | Canteen (low confidence) |
| 355636605 | 9.23 | 57.70 | 43.36 × 31.24 | Library (low confidence) |
| 355636688 | 63.44 | 56.01 | 58.95 × 41.52 | PG Block (low confidence) |
| 355636693 | -35.56 | 54.78 | 40.25 × 20.08 | Block 10 (provisional) |
| 355636694 | 76.64 | -15.60 | 43.84 × 21.06 | Block 11 (provisional) |
| 355636701 | 90.83 | 89.23 | 61.75 × 39.93 | Mechanical Block (low confidence) |
| 355636704 | 89.85 | 144.75 | 60.20 × 58.03 | Civil Block (low confidence) |
| 364147634 | -172.98 | 83.58 | 18.72 × 10.81 | Block 12 (provisional) |
| 768032824 | -217.19 | 198.06 | 17.55 × 36.95 | Hostel-tagged OSM feature outside boundary; facility identity unconfirmed |

The complete source geometry, tags, roads, boundary and local-metre conversion are in `public/data/osm-campus.json`. The app footer displays the required OSM attribution. OSM data is © OpenStreetMap contributors and available under the Open Database License; see [openstreetmap.org/copyright](https://www.openstreetmap.org/copyright).
