# CampusOps Digital Twin

An offline-capable React Three Fiber campus scene with the existing CampusOps operations panel and backend contract. The scene uses locally packaged OpenStreetMap building footprints and road traces for SRM Easwari, converted to local metres. See `OSM_BUILDING_MAPPING.md` for the candidate footprint-to-node mapping and known gaps.

## Rendering stack

- React 19.3.1, TypeScript 7.0.2, Vite 8.3.5
- Three.js 0.186.1, `@react-three/fiber` 9.8.2, `@react-three/drei` 10.7.9
- `@react-three/postprocessing` 3.2.2 and `postprocessing` 6.39.5
- ACES filmic tone mapping, a generated local sky environment, PBR materials, procedural ground textures, soft shadows, bloom/vignette, and optional high-quality N8AO

No map tiles, HDRI URLs, facade images, GLB files, or scans are required at runtime. Local facade images and GLB assets override the procedural models when present. Optional scanned scene support is off by default.

## Run

Copy `.env.example` to `.env.local` and run:

```powershell
npm install
npm run dev
npm run build
```

Set `VITE_MOCK_MODE=false` when connecting the backend. To enable an optional local scan, set `VITE_ENABLE_SCANNED_HERO=true` and restart Vite; asset naming and coordinate registration are described in `public/scans/README.md`.

## Local visual assets

- Facade images: `public/textures/<buildingId>/front.jpg` and `side.jpg`
- Hand-modelled buildings: `public/models/<buildingId>.glb`
- Optional campus scan: `public/scans/srm-campus.splat`, `.ply`, or `.glb`

OpenStreetMap attribution is displayed in the app below the campus view. OSM geometry is © OpenStreetMap contributors and available under the ODbL.
