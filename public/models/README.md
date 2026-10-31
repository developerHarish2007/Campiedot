GLB buildings
===============
Place a hand-modelled building at /public/models/<buildingId>.glb. Runtime path is /models/<buildingId>.glb. Existing CampusOps building IDs are accepted (for example building-pg); unmapped OSM context buildings use osm-way-<wayId>.glb.

Use meters, keep the model origin at the footprint center on ground level, and keep its long axis aligned to the OSM footprint. Models are fitted uniformly within the estimated footprint and height. If no file exists, the procedural PBR shell renders.
