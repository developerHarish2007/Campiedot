import { lazy, Suspense, useEffect, useState } from 'react';
import { campusApi } from '../api';
import type { CampusMapStatusResponse } from '../contracts';
import { getBlock, getBlockByNodeId, getRoom, getRoomByNodeIdOrAlias } from '../data/registry/registryService';

const CampusWorld = lazy(() => import('./CampusWorld').then(m => ({ default: m.CampusWorld })));

export function CampusMap() {
  const [snapshot, setSnapshot] = useState<CampusMapStatusResponse | null>(null);
  const [selectedId, setSelectedId] = useState('building-pg');

  // Interior navigation state (URL-synced & shared with 3D world)
  const [interiorMode, setInteriorMode] = useState<'campus' | 'cutaway' | 'diorama'>(() => {
    if (typeof window === 'undefined') return 'campus';
    const params = new URLSearchParams(window.location.search);
    const view = params.get('view');
    if (view === 'cutaway') return 'cutaway';
    if (view === 'room') return 'diorama';
    return 'campus';
  });

  const [interiorBlockId, setInteriorBlockId] = useState<string>(() => {
    if (typeof window === 'undefined') return 'PG';
    const params = new URLSearchParams(window.location.search);
    const b = params.get('block');
    if (b) {
      const blk = getBlock(b) ?? getBlockByNodeId(b);
      if (blk) return blk.blockId;
    }
    const r = params.get('room');
    if (r) {
      const rm = getRoom(r) ?? getRoomByNodeIdOrAlias(r);
      if (rm) return rm.blockId;
    }
    return 'PG';
  });

  const [interiorRoomId, setInteriorRoomId] = useState<string>(() => {
    if (typeof window === 'undefined') return 'PG-001';
    const params = new URLSearchParams(window.location.search);
    const r = params.get('room');
    if (r) {
      const rm = getRoom(r) ?? getRoomByNodeIdOrAlias(r);
      if (rm) return rm.roomId;
    }
    return 'PG-001';
  });

  const refresh = async () => {
    try {
      const s = await campusApi.getMapStatus();
      setSnapshot(s);
    } catch (e) {
      console.warn('Could not refresh campus data', e);
    }
  };

  // Parse debug URLs on mount: ?view=cutaway&block=PG or ?view=room&room=PG-101 or ?view=room&room=PG-201&lab=1
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const view = params.get('view');
    const blockParam = params.get('block');
    const roomParam = params.get('room');

    if (view === 'cutaway' && blockParam) {
      const blk = getBlock(blockParam) ?? getBlockByNodeId(blockParam);
      if (blk) {
        console.log(`[interior] entering ${blk.blockId}`);
        setInteriorBlockId(blk.blockId);
        if (blk.nodeId) setSelectedId(blk.nodeId);
        setInteriorMode('cutaway');
      }
    } else if (view === 'room' && roomParam) {
      const r = getRoom(roomParam) ?? getRoomByNodeIdOrAlias(roomParam);
      if (r) {
        console.log(`[interior] entering ${r.blockId}`);
        setInteriorBlockId(r.blockId);
        setInteriorRoomId(r.roomId);
        setInteriorMode('diorama');
      }
    }
  }, []);

  useEffect(() => {
    void refresh();
    const timer = window.setInterval(() => void refresh(), 3000);
    return () => clearInterval(timer);
  }, []);

  const handleEnterBuilding = (blockId: string) => {
    const blk = getBlock(blockId) ?? getBlockByNodeId(blockId);
    if (!blk) return;
    console.log(`[interior] entering ${blk.blockId}`);
    setInteriorBlockId(blk.blockId);
    setInteriorMode('cutaway');
    const url = new URL(window.location.href);
    url.searchParams.set('view', 'cutaway');
    url.searchParams.set('block', blk.blockId);
    url.searchParams.delete('room');
    url.searchParams.delete('lab');
    window.history.replaceState(null, '', url.toString());
  };

  return (
    <section className="map-layout">
      <div className="map-frame">
        <Suspense fallback={<div className="world-wrap world-loading"><span>Loading Campus 3D Scene...</span></div>}>
          <CampusWorld
            snapshot={snapshot}
            selectedNodeId={selectedId}
            onSelectNode={(id) => setSelectedId(id)}
            interiorMode={interiorMode}
            onInteriorModeChange={setInteriorMode}
            interiorBlockId={interiorBlockId}
            onInteriorBlockChange={setInteriorBlockId}
            interiorRoomId={interiorRoomId}
            onInteriorRoomChange={setInteriorRoomId}
            onEnterBuilding={handleEnterBuilding}
          />
        </Suspense>
        <div className="map-note">
          Real campus building footprints and roads from OpenStreetMap · estimated heights where OSM tags are missing · <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noreferrer">© OpenStreetMap contributors</a>
        </div>
      </div>
    </section>
  );
}
