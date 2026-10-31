Optional scanned hero zone
==========================
To enable, set VITE_ENABLE_SCANNED_HERO=true and restart Vite. The app checks, in order, for srm-campus.splat, srm-campus.ply, then srm-campus.glb in this folder. With the flag off or files absent, the OSM procedural scene remains active.

Register the scan in the same local-meter coordinate frame as public/data/osm-campus.json: x east, z south, origin 13.0335762 N, 80.17934165 E, ground at y=0. The current renderer places a scan at [0,0,0], scale 1. For other scan origins or scales, transform the asset before adding it. OSM footprint proxy walls drive creative-mode collision; invisible proxy floor plates use each estimated/OSM floor height. Status, selected-node, incident blast-radius, and What-If highlights are drawn on their mapped OSM footprint proxies.

A scan is optional and is not included in this repository.
