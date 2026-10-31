import React, { useMemo, useRef, useState, useEffect } from 'react';
import { useFrame, useThree } from '@react-three/fiber';
import { OrbitControls, Billboard, Text } from '@react-three/drei';
import {
  DoubleSide,
  Group,
  Mesh,
  MeshStandardMaterial,
  SRGBColorSpace
} from 'three';
import type { RegistryRoom, RegistryEquipment } from '../../data/registry/registryService';
import { getEquipmentHealthState } from '../../data/registry/registryService';
import {
  getTileTexture,
  getWallTexture,
  getWhiteboardTexture,
  getNoticeBoardTexture,
  getWoodTexture,
  disposeClassroomTextures
} from './classroomTextures';

interface DioramaProps {
  room: RegistryRoom;
  equipment: RegistryEquipment[];
  onBack: () => void;
  night?: boolean;
}

// Room dimensions in meters
const ROOM_W = 9.0;
const ROOM_D = 7.0;
const ROOM_H = 3.2;
const WALL_THICK = 0.23;

export function ClassroomDiorama({ room, equipment, onBack, night = false }: DioramaProps) {
  const [hoveredEquip, setHoveredEquip] = useState<RegistryEquipment | null>(null);

  const { camera } = useThree();
  useEffect(() => {
    camera.position.set(3.4, 2.4, 3.2);
    camera.lookAt(-0.3, 1.2, -1.0);
  }, [camera]);

  // Materials
  const tileTex = useMemo(() => getTileTexture(), []);
  const wallTex = useMemo(() => getWallTexture(), []);
  const wbTex = useMemo(() => getWhiteboardTexture(), []);
  const nbTex = useMemo(() => getNoticeBoardTexture(), []);
  const woodTex = useMemo(() => getWoodTexture(), []);

  useEffect(() => {
    return () => {
      disposeClassroomTextures();
    };
  }, []);

  const floorMat = useMemo(() => new MeshStandardMaterial({
    map: tileTex,
    roughness: 0.28,
    metalness: 0.04,
    color: '#eae7df'
  }), [tileTex]);

  const wallMat = useMemo(() => new MeshStandardMaterial({
    map: wallTex,
    roughness: 0.88,
    metalness: 0.02
  }), [wallTex]);

  const metalMat = useMemo(() => new MeshStandardMaterial({
    color: '#343836',
    roughness: 0.45,
    metalness: 0.75
  }), []);

  const woodMat = useMemo(() => new MeshStandardMaterial({
    map: woodTex,
    roughness: 0.65,
    metalness: 0.05
  }), [woodTex]);

  const glassMat = useMemo(() => new MeshStandardMaterial({
    color: '#aed0dd',
    transparent: true,
    opacity: 0.35,
    roughness: 0.1,
    metalness: 0.1
  }), []);

  useEffect(() => {
    console.log(`[interior] mounted room ${room.roomId}`);
  }, [room.roomId]);

  const urlParams = typeof window !== 'undefined' ? new URLSearchParams(window.location.search) : null;
  const forceLab = urlParams?.get('lab') === '1';
  const isSmartLab = forceLab || room.type === 'smart_lab' || equipment.length > 0;

  const projector = equipment.find(e => e.type === 'PROJECTOR') ?? (isSmartLab ? {
    equipmentId: `${room.roomId}-PROJ`,
    roomId: room.roomId,
    blockId: room.blockId,
    type: 'PROJECTOR' as const,
    displayName: 'Ceiling Multimedia Projector',
    nodeId: `equip-${room.roomId.toLowerCase()}-proj`,
    aliases: [],
    status: 'OPERATIONAL' as const,
    healthScore: 0.94,
    source: 'demo',
    createdAt: '2026-10-31T00:00:00Z'
  } : undefined);

  const ac = equipment.find(e => e.type === 'AC') ?? (isSmartLab ? {
    equipmentId: `${room.roomId}-AC`,
    roomId: room.roomId,
    blockId: room.blockId,
    type: 'AC' as const,
    displayName: '2.0 Ton Split Inverter AC',
    nodeId: `equip-${room.roomId.toLowerCase()}-ac`,
    aliases: [],
    status: 'OPERATIONAL' as const,
    healthScore: 0.88,
    source: 'demo',
    createdAt: '2026-10-31T00:00:00Z'
  } : undefined);

  const tv = equipment.find(e => e.type === 'TV') ?? (isSmartLab ? {
    equipmentId: `${room.roomId}-TV`,
    roomId: room.roomId,
    blockId: room.blockId,
    type: 'TV' as const,
    displayName: '55" Ultra-HD Interactive Smart Display',
    nodeId: `equip-${room.roomId.toLowerCase()}-tv`,
    aliases: [],
    status: 'OPERATIONAL' as const,
    healthScore: 0.96,
    source: 'demo',
    createdAt: '2026-10-31T00:00:00Z'
  } : undefined);

  return (
    <>
      <color attach="background" args={[night ? '#0f1715' : '#e6ebed']} />
      <ambientLight intensity={night ? 0.4 : 0.85} />

      {/* Daylight through left windows */}
      <directionalLight
        position={[-12, 8, 2]}
        intensity={night ? 0.15 : 1.9}
        castShadow
        shadow-mapSize={[1024, 1024]}
        shadow-bias={-0.0004}
      />

      {/* Ceiling fill & Tube light ambiance */}
      <pointLight position={[0, 2.9, 0]} intensity={night ? 1.6 : 0.9} distance={10} color="#fffcf5" />

      <group position={[0, 0, 0]}>
        {/* 1. Floor */}
        <mesh position={[0, 0, 0]} receiveShadow material={floorMat}>
          <boxGeometry args={[ROOM_W, 0.15, ROOM_D]} />
        </mesh>

        {/* 2. Front Wall with Whiteboard & Wall Clock (z = -ROOM_D / 2) */}
        <mesh position={[0, ROOM_H / 2, -ROOM_D / 2]} receiveShadow material={wallMat}>
          <boxGeometry args={[ROOM_W, ROOM_H, WALL_THICK]} />
        </mesh>

        {/* 3. Back Cutaway Threshold & Frame (z = ROOM_D / 2) */}
        {/* Low base wall */}
        <mesh position={[0, 0.45, ROOM_D / 2]} receiveShadow material={wallMat}>
          <boxGeometry args={[ROOM_W, 0.9, WALL_THICK]} />
        </mesh>
        {/* Header lintel beam */}
        <mesh position={[0, ROOM_H - 0.15, ROOM_D / 2]} material={wallMat}>
          <boxGeometry args={[ROOM_W, 0.3, WALL_THICK]} />
        </mesh>

        {/* 4. Left Wall with window openings (x = -ROOM_W / 2) */}
        {/* Left wall bottom sill */}
        <mesh position={[-ROOM_W / 2, 0.5, 0]} receiveShadow material={wallMat}>
          <boxGeometry args={[WALL_THICK, 1.0, ROOM_D]} />
        </mesh>
        {/* Left wall top lintel */}
        <mesh position={[-ROOM_W / 2, 2.85, 0]} receiveShadow material={wallMat}>
          <boxGeometry args={[WALL_THICK, 0.7, ROOM_D]} />
        </mesh>
        {/* Left wall center pier */}
        <mesh position={[-ROOM_W / 2, 1.75, 0]} receiveShadow material={wallMat}>
          <boxGeometry args={[WALL_THICK, 1.5, 1.0]} />
        </mesh>
        {/* Left wall end piers */}
        <mesh position={[-ROOM_W / 2, 1.75, -ROOM_D / 2 + 0.6]} receiveShadow material={wallMat}>
          <boxGeometry args={[WALL_THICK, 1.5, 1.2]} />
        </mesh>
        <mesh position={[-ROOM_W / 2, 1.75, ROOM_D / 2 - 0.6]} receiveShadow material={wallMat}>
          <boxGeometry args={[WALL_THICK, 1.5, 1.2]} />
        </mesh>

        {/* Windows with Indian college metal grille bars */}
        <WindowUnit position={[-ROOM_W / 2, 1.75, -1.6]} glassMat={glassMat} metalMat={metalMat} />
        <WindowUnit position={[-ROOM_W / 2, 1.75, 1.6]} glassMat={glassMat} metalMat={metalMat} />

        {/* Outdoor courtyard daylight sky & lawn backdrop outside windows */}
        <group position={[-ROOM_W / 2 - 3.0, 2.0, 0]} rotation={[0, Math.PI / 2, 0]}>
          <mesh>
            <planeGeometry args={[16, 8]} />
            <meshBasicMaterial color={night ? '#0a1017' : '#cde5f9'} />
          </mesh>
          {/* Distant green canopy and lawn */}
          <mesh position={[0, -2.4, 0.05]}>
            <planeGeometry args={[16, 3.2]} />
            <meshBasicMaterial color={night ? '#042f1a' : '#3d7224'} />
          </mesh>
        </group>

        {/* 5. Right Wall (x = ROOM_W / 2) */}
        <mesh position={[ROOM_W / 2, ROOM_H / 2, 0]} receiveShadow material={wallMat}>
          <boxGeometry args={[WALL_THICK, ROOM_H, ROOM_D]} />
        </mesh>

        {/* Door on right wall towards the back */}
        <DoorUnit position={[ROOM_W / 2 - 0.08, 1.05, 1.8]} woodMat={woodMat} metalMat={metalMat} glassMat={glassMat} />

        {/* Whiteboard on front wall (facing +Z into classroom) */}
        <group position={[0, 1.6, -ROOM_D / 2 + 0.14]}>
          <mesh position={[0, 0, 0.02]} castShadow receiveShadow>
            <planeGeometry args={[4.2, 1.4]} />
            <meshStandardMaterial map={wbTex} roughness={0.18} metalness={0.05} />
          </mesh>
          {/* Aluminum Frame */}
          <mesh position={[0, 0, 0]} material={metalMat}>
            <boxGeometry args={[4.26, 1.46, 0.03]} />
          </mesh>
          {/* Marker Tray */}
          <mesh position={[0, -0.72, 0.05]} material={metalMat}>
            <boxGeometry args={[4.2, 0.04, 0.1]} />
          </mesh>
          {/* Markers and Eraser */}
          <mesh position={[-0.4, -0.69, 0.05]}>
            <boxGeometry args={[0.15, 0.03, 0.06]} />
            <meshStandardMaterial color="#2d3748" />
          </mesh>
          <mesh position={[0.2, -0.69, 0.05]}>
            <cylinderGeometry args={[0.012, 0.012, 0.14]} />
            <meshStandardMaterial color="#c53030" />
          </mesh>
          <mesh position={[0.4, -0.69, 0.05]}>
            <cylinderGeometry args={[0.012, 0.012, 0.14]} />
            <meshStandardMaterial color="#2b6cb0" />
          </mesh>
        </group>

        {/* Notice Board on right wall */}
        <group position={[ROOM_W / 2 - 0.05, 1.7, -0.5]} rotation={[0, -Math.PI / 2, 0]}>
          <mesh position={[0, 0, 0.02]} receiveShadow>
            <planeGeometry args={[2.0, 1.2]} />
            <meshStandardMaterial map={nbTex} roughness={0.92} metalness={0.01} />
          </mesh>
          {/* Wooden Frame */}
          <mesh position={[0, 0, 0]} material={woodMat}>
            <boxGeometry args={[2.06, 1.26, 0.03]} />
          </mesh>
        </group>

        {/* Analog Wall Clock above whiteboard */}
        <WallClock position={[0, 2.65, -ROOM_D / 2 + 0.15]} />

        {/* Switchboard near the door */}
        <Switchboard position={[ROOM_W / 2 - 0.06, 1.2, 2.6]} />

        {/* Dustbin in corner */}
        <mesh position={[ROOM_W / 2 - 0.4, 0.25, -ROOM_D / 2 + 0.5]} castShadow receiveShadow>
          <cylinderGeometry args={[0.18, 0.15, 0.5, 16]} />
          <meshStandardMaterial color="#2b4c68" roughness={0.5} />
        </mesh>

        {/* Teacher's Podium / Desk */}
        <group position={[2.6, 0.45, -ROOM_D / 2 + 1.2]}>
          <mesh castShadow receiveShadow material={woodMat}>
            <boxGeometry args={[1.2, 0.85, 0.6]} />
          </mesh>
          <mesh position={[0, 0.5, 0.1]} castShadow material={woodMat}>
            <boxGeometry args={[0.4, 0.2, 0.3]} />
          </mesh>
        </group>

        {/* Student Benches & Desks arranged in rows facing front wall */}
        <StudentBenches woodMat={woodMat} metalMat={metalMat} />

        {/* Ceiling Fans (Rotating with subtle wobble) */}
        <CeilingFan position={[-1.8, 2.85, -1.0]} />
        <CeilingFan position={[1.8, 2.85, -1.0]} />
        <CeilingFan position={[0, 2.85, 1.5]} />

        {/* LED Tube Light Battens */}
        <TubeLight position={[-2.0, 3.12, -1.5]} />
        <TubeLight position={[2.0, 3.12, -1.5]} />
        <TubeLight position={[-2.0, 3.12, 1.5]} />
        <TubeLight position={[2.0, 3.12, 1.5]} />

        {/* SMART LAB EQUIPMENT (if equipped) */}
        {isSmartLab && (
          <>
            {/* 1. Ceiling Projector */}
            <group
              position={[0, 2.85, -0.6]}
              onPointerOver={(e) => { e.stopPropagation(); if (projector) setHoveredEquip(projector); }}
              onPointerOut={() => setHoveredEquip(null)}
            >
              <ProjectorUnit equipment={projector} />
              {projector && (
                <EquipmentIndicator
                  position={[0, -0.4, 0]}
                  state={getEquipmentHealthState(projector.healthScore, projector.status)}
                />
              )}
            </group>

            {/* 2. Split AC Indoor Unit (Right wall) */}
            <group
              position={[ROOM_W / 2 - 0.22, 2.5, -1.8]}
              rotation={[0, -Math.PI / 2, 0]}
              onPointerOver={(e) => { e.stopPropagation(); if (ac) setHoveredEquip(ac); }}
              onPointerOut={() => setHoveredEquip(null)}
            >
              <SplitAcUnit equipment={ac} />
              {ac && (
                <EquipmentIndicator
                  position={[0, -0.3, 0.2]}
                  state={getEquipmentHealthState(ac.healthScore, ac.status)}
                />
              )}
            </group>

            {/* Outdoor AC Condenser Unit visible outside the window */}
            <group position={[-ROOM_W / 2 - 0.5, 1.4, -1.6]} rotation={[0, Math.PI / 2, 0]}>
              <OutdoorCondenserUnit />
            </group>

            {/* 3. 55" Smart LED TV (Right wall) */}
            <group
              position={[ROOM_W / 2 - 0.08, 1.8, -0.5]}
              rotation={[0, -Math.PI / 2, 0]}
              onPointerOver={(e) => { e.stopPropagation(); if (tv) setHoveredEquip(tv); }}
              onPointerOut={() => setHoveredEquip(null)}
            >
              <SmartTvUnit equipment={tv} />
              {tv && (
                <EquipmentIndicator
                  position={[0, -0.5, 0.1]}
                  state={getEquipmentHealthState(tv.healthScore, tv.status)}
                />
              )}
            </group>
          </>
        )}
      </group>

      {/* OrbitControls from back-corner view into classroom */}
      <OrbitControls
        makeDefault
        target={[-0.2, 1.2, -0.6]}
        minDistance={3.0}
        maxDistance={12}
        minPolarAngle={Math.PI / 7}
        maxPolarAngle={Math.PI / 2.05}
        enableDamping
        dampingFactor={0.05}
      />

      {/* Hovered Equipment Health Card */}
      {hoveredEquip && (
        <Billboard position={[0, 2.6, 0]}>
          <group position={[0, 0, 0]}>
            <mesh>
              <planeGeometry args={[2.8, 1.1]} />
              <meshBasicMaterial color="#1f2937" transparent opacity={0.92} />
            </mesh>
            <Text position={[0, 0.32, 0.01]} fontSize={0.16} color="#f9fafb" anchorX="center" anchorY="middle">
              {hoveredEquip.displayName.toUpperCase()}
            </Text>
            <Text position={[0, 0.08, 0.01]} fontSize={0.13} color="#9ca3af" anchorX="center" anchorY="middle">
              {hoveredEquip.equipmentId} · {hoveredEquip.type}
            </Text>
            <Text
              position={[0, -0.22, 0.01]}
              fontSize={0.15}
              color={
                getEquipmentHealthState(hoveredEquip.healthScore, hoveredEquip.status) === 'failed'
                  ? '#ef4444'
                  : getEquipmentHealthState(hoveredEquip.healthScore, hoveredEquip.status) === 'imminent'
                  ? '#f97316'
                  : getEquipmentHealthState(hoveredEquip.healthScore, hoveredEquip.status) === 'degrading'
                  ? '#eab308'
                  : '#10b981'
              }
              anchorX="center"
              anchorY="middle"
            >
              {`Status: ${hoveredEquip.status} · Health: ${(hoveredEquip.healthScore * 100).toFixed(0)}%`}
            </Text>
          </group>
        </Billboard>
      )}
    </>
  );
}

// -------------------------------------------------------------
// Subcomponents
// -------------------------------------------------------------

function WindowUnit({ position, glassMat, metalMat }: { position: [number, number, number]; glassMat: any; metalMat: any }) {
  return (
    <group position={position}>
      {/* Outer aluminum frame perimeter */}
      {/* Top frame bar */}
      <mesh position={[0, 0.725, 0]} material={metalMat}>
        <boxGeometry args={[0.06, 0.05, 2.2]} />
      </mesh>
      {/* Bottom frame bar */}
      <mesh position={[0, -0.725, 0]} material={metalMat}>
        <boxGeometry args={[0.06, 0.05, 2.2]} />
      </mesh>
      {/* Left jamb bar */}
      <mesh position={[0, 0, -1.075]} material={metalMat}>
        <boxGeometry args={[0.06, 1.4, 0.05]} />
      </mesh>
      {/* Right jamb bar */}
      <mesh position={[0, 0, 1.075]} material={metalMat}>
        <boxGeometry args={[0.06, 1.4, 0.05]} />
      </mesh>
      {/* Center vertical mullion bar */}
      <mesh position={[0, 0, 0]} material={metalMat}>
        <boxGeometry args={[0.06, 1.4, 0.04]} />
      </mesh>

      {/* Glass pane */}
      <mesh material={glassMat}>
        <boxGeometry args={[0.01, 1.4, 2.1]} />
      </mesh>

      {/* Indian college steel grille vertical bars */}
      {[-0.8, -0.4, 0.4, 0.8].map((zOffset, idx) => (
        <mesh key={idx} position={[0, 0, zOffset]} material={metalMat}>
          <cylinderGeometry args={[0.008, 0.008, 1.4, 8]} />
        </mesh>
      ))}
      {/* Horizontal grille tie bars */}
      {[-0.35, 0.35].map((yOffset, idx) => (
        <mesh key={idx} position={[0, yOffset, 0]} rotation={[Math.PI / 2, 0, 0]} material={metalMat}>
          <cylinderGeometry args={[0.008, 0.008, 2.1, 8]} />
        </mesh>
      ))}
    </group>
  );
}

function DoorUnit({ position, woodMat, metalMat, glassMat }: { position: [number, number, number]; woodMat: any; metalMat: any; glassMat: any }) {
  return (
    <group position={position}>
      {/* Frame */}
      <mesh position={[0, 0, 0]} material={metalMat}>
        <boxGeometry args={[1.06, 2.16, 0.12]} />
      </mesh>
      {/* Solid Wood Shutter */}
      <mesh position={[0, 0, 0.01]} material={woodMat}>
        <boxGeometry args={[0.98, 2.08, 0.05]} />
      </mesh>
      {/* Vision Glass Panel */}
      <mesh position={[0.2, 0.4, 0.01]} material={glassMat}>
        <boxGeometry args={[0.25, 0.6, 0.06]} />
      </mesh>
      {/* Metal Lever Handle */}
      <mesh position={[-0.38, 0.0, 0.05]} material={metalMat}>
        <boxGeometry args={[0.12, 0.03, 0.04]} />
      </mesh>
      {/* Fire Exit Sign above door */}
      <mesh position={[0, 1.25, 0.02]}>
        <boxGeometry args={[0.4, 0.16, 0.02]} />
        <meshStandardMaterial color="#15803d" emissive="#15803d" emissiveIntensity={0.3} />
      </mesh>
    </group>
  );
}

function WallClock({ position }: { position: [number, number, number] }) {
  return (
    <group position={position}>
      {/* Rim */}
      <mesh rotation={[Math.PI / 2, 0, 0]}>
        <cylinderGeometry args={[0.24, 0.24, 0.04, 32]} />
        <meshStandardMaterial color="#1e293b" metalness={0.8} roughness={0.3} />
      </mesh>
      {/* Dial Face */}
      <mesh position={[0, 0, 0.022]} rotation={[Math.PI / 2, 0, 0]}>
        <cylinderGeometry args={[0.21, 0.21, 0.005, 32]} />
        <meshStandardMaterial color="#f8fafc" roughness={0.2} />
      </mesh>
      {/* Hour Hand (pointing near 2 o'clock) */}
      <mesh position={[0.035, 0.04, 0.03]} rotation={[0, 0, -Math.PI / 3]}>
        <boxGeometry args={[0.015, 0.09, 0.005]} />
        <meshBasicMaterial color="#000000" />
      </mesh>
      {/* Minute Hand (pointing at 12 o'clock) */}
      <mesh position={[0, 0.06, 0.032]}>
        <boxGeometry args={[0.01, 0.13, 0.005]} />
        <meshBasicMaterial color="#000000" />
      </mesh>
      {/* Center Pin */}
      <mesh position={[0, 0, 0.035]} rotation={[Math.PI / 2, 0, 0]}>
        <cylinderGeometry args={[0.012, 0.012, 0.01, 16]} />
        <meshBasicMaterial color="#dc2626" />
      </mesh>
    </group>
  );
}

function Switchboard({ position }: { position: [number, number, number] }) {
  return (
    <group position={position}>
      {/* White plate */}
      <mesh>
        <boxGeometry args={[0.22, 0.16, 0.02]} />
        <meshStandardMaterial color="#f3f4f6" roughness={0.3} />
      </mesh>
      {/* Rocker switches */}
      {[-0.05, 0.0, 0.05].map((x, i) => (
        <mesh key={i} position={[x, 0, 0.012]}>
          <boxGeometry args={[0.025, 0.05, 0.01]} />
          <meshStandardMaterial color="#e5e7eb" roughness={0.2} />
        </mesh>
      ))}
    </group>
  );
}

function CeilingFan({ position }: { position: [number, number, number] }) {
  const fanRef = useRef<Group>(null);
  const wobbleRef = useRef<Group>(null);

  useFrame((_, delta) => {
    if (fanRef.current) {
      fanRef.current.rotation.y += delta * 12.0; // Realistic rotation speed
    }
    if (wobbleRef.current) {
      // Natural slight blade wobble
      wobbleRef.current.rotation.z = Math.sin(Date.now() * 0.004) * 0.008;
    }
  });

  return (
    <group position={position} ref={wobbleRef}>
      {/* Ceiling canopy and downrod */}
      <mesh position={[0, 0.18, 0]}>
        <cylinderGeometry args={[0.06, 0.06, 0.08, 16]} />
        <meshStandardMaterial color="#e2e8f0" roughness={0.4} />
      </mesh>
      <mesh position={[0, 0.06, 0]}>
        <cylinderGeometry args={[0.012, 0.012, 0.22, 8]} />
        <meshStandardMaterial color="#cbd5e1" metalness={0.6} roughness={0.3} />
      </mesh>

      {/* Motor Hub & Rotating Blades */}
      <group position={[0, -0.06, 0]} ref={fanRef}>
        <mesh rotation={[Math.PI / 2, 0, 0]}>
          <cylinderGeometry args={[0.11, 0.11, 0.08, 24]} />
          <meshStandardMaterial color="#f1f5f9" roughness={0.3} metalness={0.1} />
        </mesh>
        {/* 3 aerodynamic blades, 1.2m sweep */}
        {[0, (2 * Math.PI) / 3, (4 * Math.PI) / 3].map((angle, idx) => (
          <group key={idx} rotation={[0, angle, 0]}>
            <mesh position={[0.32, 0, 0]} rotation={[0.08, 0, 0]}>
              <boxGeometry args={[0.55, 0.006, 0.12]} />
              <meshStandardMaterial color="#f8fafc" roughness={0.35} />
            </mesh>
          </group>
        ))}
      </group>
    </group>
  );
}

function TubeLight({ position }: { position: [number, number, number] }) {
  return (
    <group position={position}>
      {/* Aluminum mounting batten */}
      <mesh position={[0, 0.02, 0]}>
        <boxGeometry args={[1.25, 0.04, 0.08]} />
        <meshStandardMaterial color="#94a3b8" metalness={0.7} roughness={0.4} />
      </mesh>
      {/* Frosted white tube diffuser */}
      <mesh position={[0, -0.01, 0]} rotation={[0, 0, Math.PI / 2]}>
        <cylinderGeometry args={[0.018, 0.018, 1.2, 16]} />
        <meshStandardMaterial color="#ffffff" emissive="#fffdf7" emissiveIntensity={0.8} />
      </mesh>
    </group>
  );
}

/**
 * Student benches: 4 rows x 2 columns with central 0.9m aisle.
 * Includes subtle natural offset & rotation variations.
 */
function StudentBenches({ woodMat, metalMat }: { woodMat: any; metalMat: any }) {
  const units = useMemo(() => {
    const list: Array<{ x: number; z: number; rotY: number }> = [];
    const rows = 4;
    const zStart = -1.2;
    const zStep = 1.15;
    const xPositions = [-2.2, 2.2]; // 0.9m center aisle between benches of 1.6m width

    for (let r = 0; r < rows; r++) {
      const z = zStart + r * zStep;
      for (const x of xPositions) {
        // Subtle micro-variation for realism
        const jitterX = (Math.sin(r * 4.3 + x) * 0.008);
        const jitterZ = (Math.cos(r * 2.7 + x) * 0.008);
        const rotY = (Math.sin(r * 5.1 + x) * 0.012);
        list.push({ x: x + jitterX, z: z + jitterZ, rotY });
      }
    }
    return list;
  }, []);

  return (
    <group>
      {units.map((pos, idx) => (
        <group key={idx} position={[pos.x, 0, pos.z]} rotation={[0, pos.rotY, 0]}>
          {/* Desk Top */}
          <mesh position={[0, 0.74, -0.15]} castShadow receiveShadow material={woodMat}>
            <boxGeometry args={[1.6, 0.03, 0.45]} />
          </mesh>
          {/* Desk Legs (Metal Tubing) */}
          <mesh position={[-0.72, 0.36, -0.15]} material={metalMat}>
            <cylinderGeometry args={[0.016, 0.016, 0.72, 8]} />
          </mesh>
          <mesh position={[0.72, 0.36, -0.15]} material={metalMat}>
            <cylinderGeometry args={[0.016, 0.016, 0.72, 8]} />
          </mesh>
          {/* Bench Seat */}
          <mesh position={[0, 0.44, 0.22]} castShadow receiveShadow material={woodMat}>
            <boxGeometry args={[1.6, 0.03, 0.28]} />
          </mesh>
          {/* Bench Backrest */}
          <mesh position={[0, 0.68, 0.34]} castShadow material={woodMat}>
            <boxGeometry args={[1.6, 0.16, 0.02]} />
          </mesh>
          {/* Bench Legs and connectors */}
          <mesh position={[-0.72, 0.22, 0.22]} material={metalMat}>
            <cylinderGeometry args={[0.016, 0.016, 0.44, 8]} />
          </mesh>
          <mesh position={[0.72, 0.22, 0.22]} material={metalMat}>
            <cylinderGeometry args={[0.016, 0.016, 0.44, 8]} />
          </mesh>
          <mesh position={[-0.72, 0.54, 0.34]} material={metalMat}>
            <cylinderGeometry args={[0.014, 0.014, 0.24, 8]} />
          </mesh>
          <mesh position={[0.72, 0.54, 0.34]} material={metalMat}>
            <cylinderGeometry args={[0.014, 0.014, 0.24, 8]} />
          </mesh>
        </group>
      ))}
    </group>
  );
}

// -------------------------------------------------------------
// Smart Lab Units
// -------------------------------------------------------------

function ProjectorUnit({ equipment }: { equipment?: RegistryEquipment }) {
  const isFailed = equipment?.status === 'FAULTY';
  return (
    <group>
      {/* Downrod and mount */}
      <mesh position={[0, 0.15, 0]}>
        <cylinderGeometry args={[0.018, 0.018, 0.3, 8]} />
        <meshStandardMaterial color="#475569" metalness={0.7} />
      </mesh>
      {/* Projector Body */}
      <mesh position={[0, 0, 0]} castShadow>
        <boxGeometry args={[0.38, 0.12, 0.28]} />
        <meshStandardMaterial color="#f8fafc" roughness={0.3} />
      </mesh>
      {/* Lens */}
      <mesh position={[0, -0.01, -0.15]} rotation={[Math.PI / 2, 0, 0]}>
        <cylinderGeometry args={[0.04, 0.04, 0.04, 16]} />
        <meshStandardMaterial color="#0f172a" metalness={0.9} roughness={0.1} />
      </mesh>
      {/* Power / Status LED */}
      <mesh position={[0.14, 0.04, -0.13]}>
        <sphereGeometry args={[0.008, 8, 8]} />
        <meshBasicMaterial color={isFailed ? '#ef4444' : '#22c55e'} />
      </mesh>
      {/* Subtle Projection Cone (when operational) */}
      {!isFailed && (
        <mesh position={[0, -0.3, -1.8]} rotation={[-Math.PI / 8, 0, 0]}>
          <coneGeometry args={[0.8, 3.2, 16, 1, true]} />
          <meshBasicMaterial color="#ffffff" transparent opacity={0.06} side={DoubleSide} depthWrite={false} />
        </mesh>
      )}
    </group>
  );
}

function SplitAcUnit({ equipment }: { equipment?: RegistryEquipment }) {
  const isFailed = equipment?.status === 'FAULTY';
  return (
    <group>
      {/* Main indoor body */}
      <mesh castShadow receiveShadow>
        <boxGeometry args={[0.95, 0.32, 0.24]} />
        <meshStandardMaterial color="#f8fafc" roughness={0.25} />
      </mesh>
      {/* Air discharge louvers */}
      <mesh position={[0, -0.12, 0.06]}>
        <boxGeometry args={[0.86, 0.03, 0.14]} />
        <meshStandardMaterial color="#94a3b8" />
      </mesh>
      {/* LED Display Indicator (e.g. 24°C) */}
      <mesh position={[0.28, 0.02, 0.125]}>
        <planeGeometry args={[0.08, 0.04]} />
        <meshBasicMaterial color={isFailed ? '#ef4444' : '#0284c7'} />
      </mesh>
    </group>
  );
}

function OutdoorCondenserUnit() {
  return (
    <group>
      {/* Steel wall brackets */}
      <mesh position={[0, -0.35, -0.1]}>
        <boxGeometry args={[0.7, 0.04, 0.45]} />
        <meshStandardMaterial color="#475569" metalness={0.8} />
      </mesh>
      {/* Heavy-duty condenser housing */}
      <mesh castShadow receiveShadow position={[0, 0, 0]}>
        <boxGeometry args={[0.75, 0.55, 0.32]} />
        <meshStandardMaterial color="#cbd5e1" metalness={0.4} roughness={0.6} />
      </mesh>
      {/* Fan exhaust grille */}
      <mesh position={[0, 0, 0.165]} rotation={[Math.PI / 2, 0, 0]}>
        <cylinderGeometry args={[0.2, 0.2, 0.02, 24]} />
        <meshStandardMaterial color="#334155" metalness={0.7} />
      </mesh>
    </group>
  );
}

function SmartTvUnit({ equipment }: { equipment?: RegistryEquipment }) {
  const isFailed = equipment?.status === 'FAULTY';
  return (
    <group>
      {/* Thin black bezel frame */}
      <mesh castShadow>
        <boxGeometry args={[1.25, 0.72, 0.04]} />
        <meshStandardMaterial color="#0f172a" metalness={0.9} roughness={0.2} />
      </mesh>
      {/* Screen Display */}
      <mesh position={[0, 0, 0.022]}>
        <planeGeometry args={[1.21, 0.68]} />
        <meshStandardMaterial
          color={isFailed ? '#050505' : '#1e3a5f'}
          emissive={isFailed ? '#000000' : '#1e3a5f'}
          emissiveIntensity={isFailed ? 0 : 0.35}
          roughness={0.15}
        />
      </mesh>
      {/* Power LED */}
      <mesh position={[0.58, -0.33, 0.025]}>
        <sphereGeometry args={[0.005, 8, 8]} />
        <meshBasicMaterial color={isFailed ? '#ef4444' : '#22c55e'} />
      </mesh>
    </group>
  );
}

function EquipmentIndicator({ position, state }: { position: [number, number, number]; state: string }) {
  const color =
    state === 'failed' ? '#ef4444' :
    state === 'imminent' ? '#f97316' :
    state === 'degrading' ? '#eab308' : '#10b981';

  return (
    <group position={position}>
      <mesh>
        <sphereGeometry args={[0.06, 16, 16]} />
        <meshBasicMaterial color={color} />
      </mesh>
      {/* Halo ring */}
      <mesh rotation={[Math.PI / 2, 0, 0]}>
        <ringGeometry args={[0.08, 0.11, 24]} />
        <meshBasicMaterial color={color} transparent opacity={0.65} side={DoubleSide} />
      </mesh>
    </group>
  );
}
