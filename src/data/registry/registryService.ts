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

export function exportRoomsCsv(): string {
  const headers = ['roomId', 'blockId', 'floor', 'displayName', 'type', 'hasEquipment'];
  const rows = campusRegistry.rooms.map(r =>
    [r.roomId, r.blockId, r.floor, `"${r.displayName}"`, r.type, r.hasEquipment ? 'true' : 'false'].join(',')
  );
  return [headers.join(','), ...rows].join('\n');
}

export function downloadRegistryFiles() {
  // Download JSON
  const jsonBlob = new Blob([JSON.stringify(campusRegistry, null, 2)], { type: 'application/json' });
  const jsonUrl = URL.createObjectURL(jsonBlob);
  const aJson = document.createElement('a');
  aJson.href = jsonUrl;
  aJson.download = 'campusRegistry.json';
  aJson.click();
  URL.revokeObjectURL(jsonUrl);

  // Download CSV
  setTimeout(() => {
    const csvBlob = new Blob([exportRoomsCsv()], { type: 'text/csv' });
    const csvUrl = URL.createObjectURL(csvBlob);
    const aCsv = document.createElement('a');
    aCsv.href = csvUrl;
    aCsv.download = 'rooms.csv';
    aCsv.click();
    URL.revokeObjectURL(csvUrl);
  }, 100);
}

