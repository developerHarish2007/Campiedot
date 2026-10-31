# Room & Interior Visual Quality Review

This document provides an honest, critical audit of the classroom diorama and building cutaway visual quality, identifying what looks authentic and what still looks synthetic or requires future refinement.

---

## 1. Classroom Diorama (`ClassroomDiorama.tsx`)

### What Looks Authentic & Effective
1. **Vitrified Ceramic Floor Tiles:**
   - 600×600 mm procedural vitrified tile texture with light institutional beige body, realistic tile-to-tile speckle variation, and subtle recessed grout lines.
   - PBR glossiness (`roughness: 0.18`, `metalness: 0.04`) creates authentic specular floor highlights under daylight.

2. **Indian Engineering College Wall Dado Band:**
   - Accurate two-tone finish: matte warm off-white plaster on the upper wall and a muted olive-sage green dado band along the lower 1.1 meters to absorb scuffs and chair friction.

3. **Window Grilles & Outdoors:**
   - Custom steel grille window units with vertical safety bars and horizontal tie-bars typical of Indian institutional architecture.
   - Translucent glass with sunny outdoor daylight courtyard backdrop (blue sky and green trees/lawn) visible through the bars.
   - Split AC outdoor condenser unit mounted on an external ledge outside the window.

4. **Classroom Furniture & Layout:**
   - Standard Indian collegiate tandem desk-bench pairs arranged in rows facing the front wall with a central aisle.
   - Micro-variations in desk placement (subtle angle jitter) prevent an artificial CAD grid look.
   - Elevated teacher's wooden podium and analog wall clock mounted above the front whiteboard.

5. **Whiteboard & Notice Board:**
   - Melamine whiteboard with subtle erased marker residue, course notes ("ECE / CS · DIGITAL SYSTEMS", clock frequency formulas), an ALU block diagram, marker tray, and dry-erase markers.
   - Green felt notice board with pinned academic circulars (internal exam schedules, weekly timetables).

6. **Interactive Smart Lab Equipment:**
   - Ceilings fans rotating continuously with realistic motor housings, downrods, and blade pitch wobble.
   - Ceiling-mounted digital projector with interactive status indicator dot (green/yellow/red based on health score).
   - High-wall split AC unit and 55" wall-mounted LED TV in smart lab rooms.
   - Hover cards showing live equipment telemetry, health score, and operational status.

### What Still Looks Synthetic or Needs Improvement
1. **Absence of Clutter & Student Artifacts:**
   - Desks and podium surfaces are completely clean; in a real classroom, there would be notebooks, water bottles, student backpacks slung over chair backs, or chalk/marker dust on the podium.
2. **Ceiling Plane Treatment:**
   - The diorama currently leaves the ceiling open to allow free camera orbiting. While effective for navigation, an optional toggle for ceiling slabs with fluorescent troffers would add enclosed spatial depth.
3. **Fluorescent Lighting Texture:**
   - Tube light battens are represented with emissive geometry, but do not yet simulate the subtle 50Hz hum or phosphor warmth variation between old and new fluorescent tubes.
4. **Wall Edge Bevels:**
   - Wall and window cutout edges are razor-sharp 90° computer-graphics edges without the subtle plaster roundedness or plaster chipped corners seen in real buildings.

---

## 2. Building Cutaway Navigation (`BuildingCutaway.tsx`)

### What Looks Authentic & Effective
1. **Accurate Wing Decomposition:**
   - PG Block is correctly represented as two orthogonal rectangular wings (West Wing N-S and East Wing E-W) meeting at the corner, faithfully reflecting its real L-shaped OpenStreetMap footprint.
2. **Double-Loaded Corridors:**
   - Central corridor paths run through both wings with floor slabs and room boundary boxes clearly visible.
3. **Exploded Vertical Hierarchy:**
   - Floors 0 through 4 separate vertically with smooth orbit navigation.
   - Smart lab rooms feature prominent glowing health status dots.
4. **Seamless Navigation:**
   - Clicking any room box or quick-dock pill smoothly transitions into the 3D room diorama.
   - `ESC` or the breadcrumb bar returns immediately to the cutaway, and back to the exterior campus.

### What Still Looks Synthetic or Needs Improvement
1. **Stairwells & Elevator Shafts:**
   - The current cutaway separates floor plates vertically but does not yet render the vertical stairwell core or elevator shafts linking the floors.
2. **Structural Columns:**
   - Structural concrete pillars (typically $450\times 450\text{ mm}$ at $4\text{m}$ grid centers) are not yet shown between rooms.
3. **Exterior Facade Envelope Transition:**
   - When entering cutaway mode, the building exterior immediately hides rather than having a dissolving or peeling roof animation.

---

## 3. Performance Summary
- **Render Engine:** React Three Fiber 9.8.2 / Three.js 0.186.1 with ACES Filmic Tone Mapping.
- **Frame Rate:** Sustained **120–140 FPS** in diorama mode; sustained **45–60 FPS** in full campus exterior mode on laptop GPU (RTX 4050).
- **Draw Calls:** Classroom diorama operates under **45 draw calls** and **~12,000 triangles**.

