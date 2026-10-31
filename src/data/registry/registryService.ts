import campusRegistryRaw from './campusRegistry.json';

export interface RegistryBlock {
  blockId: string;
  displayName: string;
  nodeId: string;
  osmWayId: number;
  floors: number;
  roomCount: number;
  aliases: string[];
  source: string;
  category?: 'academic' | 'facility' | 'unnamed' | string;
  nameSource?: 'verified' | 'unverified' | 'unnamed' | string;
  hasRooms?: boolean;
  createdAt: string;
}

export interface RegistryFloor {
  floorId: string;
  blockId: string;
  floorNumber: number;
  displayName: string;
  source: string;
  createdAt: string;
}

export type RoomType = 'classroom' | 'lecture_hall' | 'smart_lab';

export interface RegistryRoom {
  roomId: string;
  blockId: string;
  floor: number;
  displayName: string;
  type: RoomType;
  capacity: number;
  nodeId: string;
  aliases: string[];
  hasEquipment: boolean;
  source: string;
  createdAt: string;
}

export type EquipmentType = 'PROJECTOR' | 'AC' | 'TV';
export type EquipmentHealthState = 'healthy' | 'degrading' | 'imminent' | 'failed';

export interface RegistryEquipment {
  equipmentId: string;
  roomId: string;
  blockId: string;
  type: EquipmentType;
  displayName: string;
  nodeId: string;
  aliases: string[];
  status: 'OPERATIONAL' | 'FAULTY' | 'MAINTENANCE';
  healthScore: number;
  source: string;
  createdAt: string;
}

export interface CampusRegistry {
  version: string;
  campusId: string;
  campusName: string;
  generatedAt: string;
  blocks: RegistryBlock[];
  floors: RegistryFloor[];
  rooms: RegistryRoom[];
  equipment: RegistryEquipment[];
}

export const campusRegistry: CampusRegistry = campusRegistryRaw as CampusRegistry;

export function getEquipmentHealthState(healthScore: number, status: string): EquipmentHealthState {
  if (status === 'FAULTY' || healthScore <= 0.35) return 'failed';
  if (healthScore <= 0.60) return 'imminent';
  if (healthScore <= 0.85) return 'degrading';
  return 'healthy';
}

export function getBlock(blockId: string): RegistryBlock | undefined {
  return campusRegistry.blocks.find(b => b.blockId === blockId || b.aliases.includes(blockId));
}

export function getBlockByNodeId(nodeId: string): RegistryBlock | undefined {
  return campusRegistry.blocks.find(b => b.nodeId === nodeId || b.aliases.includes(nodeId));
}

export function getBlockByOsmWay(osmWayId: number): RegistryBlock | undefined {
  return campusRegistry.blocks.find(b => b.osmWayId === osmWayId);
}

export function getRoomsForBlock(blockId: string): RegistryRoom[] {
  return campusRegistry.rooms.filter(r => r.blockId === blockId);
}

export function getRoomsForFloor(blockId: string, floor: number): RegistryRoom[] {
  return campusRegistry.rooms.filter(r => r.blockId === blockId && r.floor === floor);
}

export function getRoom(roomId: string): RegistryRoom | undefined {
  return campusRegistry.rooms.find(r => r.roomId === roomId || r.aliases.includes(roomId));
}

export function getRoomByNodeIdOrAlias(id: string): RegistryRoom | undefined {
  return campusRegistry.rooms.find(r => r.nodeId === id || r.roomId === id || r.aliases.includes(id));
}

export function getEquipmentForRoom(roomId: string): RegistryEquipment[] {
  return campusRegistry.equipment.filter(e => e.roomId === roomId || e.aliases.includes(roomId));
}

// Ordered strictly per requirement: named academic blocks, then facilities, then remaining unnamed footprints
export function getOrderedCampusBlocks(): RegistryBlock[] {
  const academic = campusRegistry.blocks.filter(b => b.category === 'academic' || (b.roomCount > 0 && b.category !== 'facility'));
  const facilities = campusRegistry.blocks.filter(b => b.category === 'facility' || ['CANTEEN', 'TNP', 'AUD', 'LIB', 'HOSTEL'].includes(b.blockId));
  const unnamed = campusRegistry.blocks.filter(b => b.category === 'unnamed' || b.blockId.startsWith('OSM-'));
  return [...academic, ...facilities, ...unnamed];
}

export function exportRoomsCsv(): string {
  const headers = ['roomId', 'blockId', 'floor', 'displayName', 'type', 'hasEquipment'];
  const rows = campusRegistry.rooms.map(r =>
    [r.roomId, r.blockId, r.floor, `"${r.displayName}"`, r.type, r.hasEquipment ? 'true' : 'false'].join(',')
  );
  return [headers.join(','), ...rows].join('\n');
}

export function exportBlocksCsv(): string {
  const headers = ['blockId', 'displayName', 'nameSource', 'hasRooms', 'osmWayId'];
  const rows = campusRegistry.blocks.map(b => {
    const hasRooms = b.hasRooms ?? (b.roomCount > 0);
    const nameSrc = b.nameSource ?? (b.blockId.startsWith('OSM-') ? 'unnamed' : 'verified');
    return [b.blockId, `"${b.displayName}"`, nameSrc, hasRooms ? 'true' : 'false', b.osmWayId].join(',');
  });
  return [headers.join(','), ...rows].join('\n');
}

export function downloadRegistryFiles() {
  // 1. Download JSON
  const jsonBlob = new Blob([JSON.stringify(campusRegistry, null, 2)], { type: 'application/json' });
  const jsonUrl = URL.createObjectURL(jsonBlob);
  const aJson = document.createElement('a');
  aJson.href = jsonUrl;
  aJson.download = 'campusRegistry.json';
  aJson.click();
  URL.revokeObjectURL(jsonUrl);

  // 2. Download rooms.csv
  setTimeout(() => {
    const csvBlob = new Blob([exportRoomsCsv()], { type: 'text/csv' });
    const csvUrl = URL.createObjectURL(csvBlob);
    const aCsv = document.createElement('a');
    aCsv.href = csvUrl;
    aCsv.download = 'rooms.csv';
    aCsv.click();
    URL.revokeObjectURL(csvUrl);
  }, 100);

  // 3. Download blocks.csv
  setTimeout(() => {
    const blocksBlob = new Blob([exportBlocksCsv()], { type: 'text/csv' });
    const blocksUrl = URL.createObjectURL(blocksBlob);
    const aBlocks = document.createElement('a');
    aBlocks.href = blocksUrl;
    aBlocks.download = 'blocks.csv';
    aBlocks.click();
    URL.revokeObjectURL(blocksUrl);
  }, 200);
}
