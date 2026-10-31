import React, { useMemo, useState, useEffect } from 'react';
import { useThree } from '@react-three/fiber';
import { OrbitControls, Billboard, Text } from '@react-three/drei';
import { BoxGeometry as THREE_BoxGeometry, DoubleSide, MeshStandardMaterial, Color } from 'three';
import type { RegistryBlock, RegistryRoom, RegistryEquipment } from '../../data/registry/registryService';
import { getEquipmentHealthState } from '../../data/registry/registryService';
import { dashboardBridge } from '../../services/dashboardBridge';

import type { DevicePrediction } from '../../sim/projectorPredictor';

interface CutawayProps {
  block: RegistryBlock;
  rooms: RegistryRoom[];
  equipment: RegistryEquipment[];
  predictions?: Record<string, DevicePrediction>;
  onSelectRoom: (roomId: string) => void;
  onBack: () => void;
  night?: boolean;
}

const DEFAULT_FLOOR_SPACING = 5.2;

export function BuildingCutaway({
  block,
  rooms,
  equipment,
  predictions,
  onSelectRoom,
  onBack,
  night = false
}: CutawayProps) {
  const [selectedFloor, setSelectedFloor] = useState<number | 'all'>('all');
  const [hoveredRoomId, setHoveredRoomId] = useState<string | null>(null);
  const [floorSeparation, setFloorSeparation] = useState(DEFAULT_FLOOR_SPACING);
  const [, setBridgeTick] = useState(0);

  useEffect(() => {
    return dashboardBridge.subscribe(() => setBridgeTick(t => t + 1));
  }, []);

  const floorCount = block.floors;
  const isPgBlock = block.blockId === 'PG';

  const { camera } = useThree();
  useEffect(() => {
    console.log(`[interior] entering ${block.blockId}`);
    if (isPgBlock) {
      camera.position.set(52, 22, 50);
      camera.lookAt(6, 11, -3);
    } else {
      camera.position.set(44, 34, 44);
      camera.lookAt(0, (floorCount * floorSeparation) / 2 + 1, 0);
    }
  }, [camera, block.blockId, isPgBlock, floorCount, floorSeparation]);

  // Group rooms by floor
  const roomsByFloor = useMemo(() => {
    const map = new Map<number, RegistryRoom[]>();
    for (let f = 0; f < floorCount; f++) {
      map.set(f, rooms.filter(r => r.floor === f));
    }
    return map;
  }, [floorCount, rooms]);

  return (
    <>
      <color attach="background" args={[night ? '#0f1715' : '#eef2f5']} />
      <ambientLight intensity={night ? 0.45 : 0.9} />
      <directionalLight position={[30, 50, 40]} intensity={1.5} castShadow shadow-mapSize={[1024, 1024]} />
      <directionalLight position={[-30, 20, -20]} intensity={0.4} />

      <group position={[0, 4.5, 0]}>
        {Array.from({ length: floorCount }, (_, f) => {
          if (selectedFloor !== 'all' && selectedFloor !== f) return null;
          const yPos = selectedFloor === 'all' ? f * floorSeparation : 0;
          const floorRooms = roomsByFloor.get(f) ?? [];

          return (
            <group key={f} position={[0, yPos, 0]}>
              {/* Floor Slab */}
              {isPgBlock ? (
                <PgFloorSlab floorIndex={f} />
              ) : (
                <StandardFloorSlab floorIndex={f} blockId={block.blockId} />
              )}

              {/* Floor Badge / Label */}
              <Billboard position={[-20, 1.2, 0]}>
                <Text fontSize={1.1} color="#334155" outlineWidth={0.05} outlineColor="#ffffff" anchorX="right">
                  {f === 0 ? 'GROUND FLOOR' : `FLOOR ${f}`}
                </Text>
              </Billboard>

              {/* Rooms layout */}
              {isPgBlock ? (
                <PgRoomsLayout
                  rooms={floorRooms}
                  equipment={equipment}
                  predictions={predictions}
                  hoveredRoomId={hoveredRoomId}
                  onHoverRoom={setHoveredRoomId}
                  onSelectRoom={onSelectRoom}
                />
              ) : (
                <StandardRoomsLayout
                  rooms={floorRooms}
                  equipment={equipment}
                  hoveredRoomId={hoveredRoomId}
                  onHoverRoom={setHoveredRoomId}
                  onSelectRoom={onSelectRoom}
                />
              )}
            </group>
          );
        })}
      </group>

      <OrbitControls
        makeDefault
        target={isPgBlock ? [8, selectedFloor === 'all' ? 12 : 0, -4] : [0, selectedFloor === 'all' ? (floorCount * floorSeparation) / 2 + 1 : 0, 0]}
        minDistance={15}
        maxDistance={120}
        maxPolarAngle={Math.PI / 2.05}
        enableDamping
        dampingFactor={0.05}
      />
    </>
  );
}

// -------------------------------------------------------------
// PG Block Floor Slab & Layout (Two Rectangular Wings)
// -------------------------------------------------------------

function PgFloorSlab({ floorIndex }: { floorIndex: number }) {
  return (
    <group>
      {/* West Wing Slab (N-S): 20m wide x 36m long */}
      <mesh position={[-8, -0.15, -4]} receiveShadow>
        <boxGeometry args={[20, 0.3, 36]} />
        <meshStandardMaterial color="#cbd5e1" roughness={0.6} />
      </mesh>
      {/* East Wing Slab (E-W): 32m long x 16m wide */}
      <mesh position={[18, -0.15, 6]} receiveShadow>
        <boxGeometry args={[32, 0.3, 16]} />
        <meshStandardMaterial color="#cbd5e1" roughness={0.6} />
      </mesh>

      {/* Central Corridors */}
      {/* West Wing Corridor */}
      <mesh position={[-8, 0.02, -4]} rotation={[-Math.PI / 2, 0, 0]}>
        <planeGeometry args={[2.4, 34]} />
        <meshStandardMaterial color="#94a3b8" roughness={0.4} />
      </mesh>
      {/* East Wing Corridor */}
      <mesh position={[18, 0.02, 6]} rotation={[-Math.PI / 2, 0, 0]}>
        <planeGeometry args={[30, 2.4]} />
        <meshStandardMaterial color="#94a3b8" roughness={0.4} />
      </mesh>
    </group>
  );
}

function PgRoomsLayout({
  rooms,
  equipment,
  predictions,
  hoveredRoomId,
  onHoverRoom,
  onSelectRoom
}: {
  rooms: RegistryRoom[];
  equipment: RegistryEquipment[];
  predictions?: Record<string, DevicePrediction>;
  hoveredRoomId: string | null;
  onHoverRoom: (id: string | null) => void;
  onSelectRoom: (id: string) => void;
}) {
  // Distribute rooms into West Wing (rooms 1 & 2) and East Wing (rooms 3 & 4)
  const roomSlots = useMemo(() => {
    return [
      { x: -14, z: -8, w: 8, d: 10 },   // West Wing Left (e.g. Smart Lab PG 001 / A101)
      { x: -2, z: -8, w: 8, d: 10 },    // West Wing Right
      { x: 10, z: 11, w: 9, d: 6 },     // East Wing South
      { x: 23, z: 11, w: 9, d: 6 }      // East Wing South East
    ];
  }, []);

  return (
    <group>
      {rooms.map((room, idx) => {
        const slot = roomSlots[idx % roomSlots.length];
        const roomEquip = equipment.filter(e => e.roomId === room.roomId);
        const smartLab = room.type === 'smart_lab' || roomEquip.length > 0;
        const isHovered = hoveredRoomId === room.roomId;

        const openReportCount = dashboardBridge.getOpenReportCount(room.roomId);
        const hasOpenReport = openReportCount > 0;

        // Health state (dynamic from projector predictor if available)
        const pred = predictions?.[`${room.roomId}-PROJ`];
        const worstHealth = pred ? pred.healthState : roomEquip.reduce((prev, curr) => {
          const state = getEquipmentHealthState(curr.healthScore, curr.status);
          if (state === 'failed') return 'failed';
          if (state === 'imminent' && prev !== 'failed') return 'imminent';
          if (state === 'degrading' && prev === 'healthy') return 'degrading';
          return prev;
        }, 'healthy');

        const isWarning = worstHealth === 'degrading' || worstHealth === 'imminent';

        return (
          <group
            key={room.roomId}
            position={[slot.x, 0, slot.z]}
          >
            {/* Room Floor Cutaway Box */}
            <mesh
              position={[0, 0.45, 0]}
              onClick={(e) => { e.stopPropagation(); onSelectRoom(room.roomId); }}
              onPointerOver={(e) => { e.stopPropagation(); onHoverRoom(room.roomId); document.body.style.cursor = 'pointer'; }}
              onPointerOut={() => { onHoverRoom(null); document.body.style.cursor = ''; }}
            >
              <boxGeometry args={[slot.w, 0.9, slot.d]} />
              <meshStandardMaterial
                color={hasOpenReport ? '#ef4444' : isWarning ? '#fde047' : isHovered ? '#fef08a' : smartLab ? '#e0f2fe' : '#f8fafc'}
                roughness={0.4}
                transparent
                opacity={hasOpenReport ? 0.95 : 0.88}
              />
            </mesh>

            {/* Perimeter Low Cutaway Wall Outline */}
            <lineSegments>
              <edgesGeometry args={[new (THREE_BoxGeometry as any)(slot.w, 0.9, slot.d)]} />
              <lineBasicMaterial
                color={hasOpenReport ? '#991b1b' : isWarning ? '#eab308' : isHovered ? '#ca8a04' : smartLab ? '#0284c7' : '#64748b'}
                linewidth={hasOpenReport || isWarning || isHovered ? 2.5 : 1}
              />
            </lineSegments>

            {/* Room Label Badge */}
            <Billboard
              position={[0, hasOpenReport ? 1.7 : 1.3, 0]}
              onClick={(e) => { e.stopPropagation(); onSelectRoom(room.roomId); }}
              onPointerOver={() => { onHoverRoom(room.roomId); document.body.style.cursor = 'pointer'; }}
              onPointerOut={() => { onHoverRoom(null); document.body.style.cursor = ''; }}
            >
              <group>
                <mesh>
                  <planeGeometry args={[hasOpenReport ? 2.8 : 2.2, 0.65]} />
                  <meshBasicMaterial
                    color={hasOpenReport ? '#dc2626' : isWarning ? '#854d0e' : isHovered ? '#1e293b' : '#334155'}
                    transparent
                    opacity={0.95}
                  />
                </mesh>
                <Text position={[0, 0.08, 0.01]} fontSize={0.22} color="#ffffff" anchorX="center" anchorY="middle">
                  {room.displayName}
                </Text>
                <Text position={[0, -0.15, 0.01]} fontSize={0.13} color="#ffffff" anchorX="center" anchorY="middle">
                  {hasOpenReport
                    ? `🚨 ${openReportCount} Needs monitoring`
                    : isWarning
                    ? '⚡ Degraded'
                    : smartLab
                    ? '★ SMART LAB'
                    : room.type.toUpperCase()}
                </Text>
              </group>
            </Billboard>

            {/* Status Indicator Marker (Red for Report, Yellow for Degraded/Imminent) */}
            {(smartLab || hasOpenReport || isWarning) && (
              <HealthStatusDot
                position={[slot.w / 2 - 0.4, 1.4, slot.d / 2 - 0.4]}
                state={worstHealth}
                reportCount={openReportCount}
              />
            )}
          </group>
        );
      })}
    </group>
  );
}

// -------------------------------------------------------------
// Standard Rectangular Block Floor Slab & Layout
// -------------------------------------------------------------

function StandardFloorSlab({ floorIndex, blockId }: { floorIndex: number; blockId: string }) {
  return (
    <group>
      {/* 40m wide x 22m deep floor slab */}
      <mesh position={[0, -0.15, 0]} receiveShadow>
        <boxGeometry args={[42, 0.3, 24]} />
        <meshStandardMaterial color="#cbd5e1" roughness={0.6} />
      </mesh>
      {/* Central longitudinal corridor */}
      <mesh position={[0, 0.02, 0]} rotation={[-Math.PI / 2, 0, 0]}>
        <planeGeometry args={[40, 2.4]} />
        <meshStandardMaterial color="#94a3b8" roughness={0.4} />
      </mesh>
    </group>
  );
}

function StandardRoomsLayout({
  rooms,
  equipment,
  hoveredRoomId,
  onHoverRoom,
  onSelectRoom
}: {
  rooms: RegistryRoom[];
  equipment: RegistryEquipment[];
  hoveredRoomId: string | null;
  onHoverRoom: (id: string | null) => void;
  onSelectRoom: (id: string) => void;
}) {
  const count = rooms.length;
  const half = Math.ceil(count / 2);

  return (
    <group>
      {rooms.map((room, idx) => {
        const isNorth = idx < half;
        const col = isNorth ? idx : idx - half;
        const totalInRow = isNorth ? half : count - half;
        const w = Math.min(36 / Math.max(1, totalInRow), 8.5);
        const x = -17 + col * (w + 0.5) + w / 2;
        const z = isNorth ? -6.2 : 6.2;
        const d = 8.5;
        const isHovered = hoveredRoomId === room.roomId;

        const openReportCount = dashboardBridge.getOpenReportCount(room.roomId);
        const hasOpenReport = openReportCount > 0;

        return (
          <group
            key={room.roomId}
            position={[x, 0, z]}
          >
            <mesh
              position={[0, 0.45, 0]}
              onClick={(e) => { e.stopPropagation(); onSelectRoom(room.roomId); }}
              onPointerOver={(e) => { e.stopPropagation(); onHoverRoom(room.roomId); document.body.style.cursor = 'pointer'; }}
              onPointerOut={() => { onHoverRoom(null); document.body.style.cursor = ''; }}
            >
              <boxGeometry args={[w, 0.9, d]} />
              <meshStandardMaterial
                color={hasOpenReport ? '#fca5a5' : isHovered ? '#fef08a' : '#f8fafc'}
                roughness={0.5}
                transparent
                opacity={0.88}
              />
            </mesh>
            <lineSegments>
              <edgesGeometry args={[new (THREE_BoxGeometry as any)(w, 0.9, d)]} />
              <lineBasicMaterial
                color={hasOpenReport ? '#dc2626' : isHovered ? '#ca8a04' : '#64748b'}
                linewidth={hasOpenReport || isHovered ? 2.5 : 1}
              />
            </lineSegments>
            <Billboard
              position={[0, 1.3, 0]}
              onClick={(e) => { e.stopPropagation(); onSelectRoom(room.roomId); }}
              onPointerOver={() => { onHoverRoom(room.roomId); document.body.style.cursor = 'pointer'; }}
              onPointerOut={() => { onHoverRoom(null); document.body.style.cursor = ''; }}
            >
              <group>
                <mesh>
                  <planeGeometry args={[2.0, 0.6]} />
                  <meshBasicMaterial color={isHovered ? '#1e293b' : hasOpenReport ? '#7f1d1d' : '#334155'} transparent opacity={0.9} />
                </mesh>
                <Text position={[0, 0.08, 0.01]} fontSize={0.2} color="#ffffff" anchorX="center" anchorY="middle">
                  {room.displayName}
                </Text>
                <Text position={[0, -0.14, 0.01]} fontSize={0.12} color={hasOpenReport ? '#fca5a5' : '#cbd5e1'} anchorX="center" anchorY="middle">
                  {hasOpenReport ? `🚨 ${openReportCount} REPORT` : room.type.toUpperCase()}
                </Text>
              </group>
            </Billboard>

            {hasOpenReport && (
              <HealthStatusDot
                position={[w / 2 - 0.4, 1.4, d / 2 - 0.4]}
                state="failed"
                reportCount={openReportCount}
              />
            )}
          </group>
        );
      })}
    </group>
  );
}

// -------------------------------------------------------------
// Equipment Health Dot Indicator
// -------------------------------------------------------------

function HealthStatusDot({
  position,
  state,
  reportCount = 0
}: {
  position: [number, number, number];
  state: string;
  reportCount?: number;
}) {
  const hasReport = reportCount > 0;
  const isWarning = state === 'degrading' || state === 'imminent';

  // Red wins if report exists, else yellow if degraded/imminent, else green
  const color = hasReport ? '#ef4444' :
    state === 'failed' ? '#ef4444' :
    state === 'imminent' ? '#eab308' :
    state === 'degrading' ? '#eab308' : '#10b981';

  return (
    <group position={position}>
      <mesh>
        <sphereGeometry args={[0.26, 16, 16]} />
        <meshBasicMaterial color={color} />
      </mesh>
      {/* Outer Glow Ring */}
      <mesh rotation={[Math.PI / 2, 0, 0]}>
        <ringGeometry args={[0.3, 0.44, 24]} />
        <meshBasicMaterial color={color} transparent opacity={0.65} side={DoubleSide} />
      </mesh>

      {/* Badge when report or warning */}
      {(hasReport || isWarning) && (
        <Billboard position={[0, 0.65, 0]}>
          <group>
            <mesh>
              <planeGeometry args={[hasReport ? 2.3 : 1.4, 0.42]} />
              <meshBasicMaterial color={hasReport ? '#991b1b' : '#854d0e'} />
            </mesh>
            <Text position={[0, 0, 0.01]} fontSize={0.16} color="#ffffff" anchorX="center" anchorY="middle">
              {hasReport ? `🚨 ${reportCount} Needs monitoring` : `⚡ Degraded`}
            </Text>
          </group>
        </Billboard>
      )}
    </group>
  );
}
