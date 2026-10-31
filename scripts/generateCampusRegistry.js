import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const targetPath = path.resolve(__dirname, '../src/data/registry/campusRegistry.json');

export function generateCampusRegistry(force = false) {
  if (fs.existsSync(targetPath) && !force) {
    console.log('campusRegistry.json already exists. Per immutability spec, skipping generation.');
    return;
  }

  const fixedDate = '2026-10-31T00:00:00Z';

  const blocks = [
    {
      blockId: 'PG',
      displayName: 'PG Block',
      nodeId: 'building-pg',
      osmWayId: 355636688,
      floors: 5,
      roomCount: 17,
      aliases: ['building-pg', 'PG Block', 'Civil & PG Block'],
      source: 'srmeaswari.ac.in/mandatory-disclosure',
      createdAt: fixedDate
    },
    {
      blockId: 'MAIN',
      displayName: 'Main Block',
      nodeId: 'building-main',
      osmWayId: 355617963,
      floors: 5,
      roomCount: 41,
      aliases: ['building-main', 'Main Block', 'Administrative Block'],
      source: 'srmeaswari.ac.in/mandatory-disclosure',
      createdAt: fixedDate
    },
    {
      blockId: 'CIVIL',
      displayName: 'Civil Block',
      nodeId: 'building-civil',
      osmWayId: 355636704,
      floors: 4,
      roomCount: 24,
      aliases: ['building-civil', 'Civil Block'],
      source: 'srmeaswari.ac.in/mandatory-disclosure',
      createdAt: fixedDate
    },
    {
      blockId: 'ECE',
      displayName: 'Electronics Block',
      nodeId: 'building-electronics',
      osmWayId: 355636432,
      floors: 4,
      roomCount: 10,
      aliases: ['building-electronics', 'Electronics Block', 'ECE Block'],
      source: 'srmeaswari.ac.in/mandatory-disclosure',
      createdAt: fixedDate
    },
    {
      blockId: 'MECH',
      displayName: 'Mechanical Block',
      nodeId: 'building-mechanical',
      osmWayId: 355636701,
      floors: 3,
      roomCount: 11,
      aliases: ['building-mechanical', 'Mechanical Block'],
      source: 'srmeaswari.ac.in/mandatory-disclosure',
      createdAt: fixedDate
    },
    {
      blockId: 'HOSTEL',
      displayName: 'Boys Hostel',
      nodeId: 'landmark-hostel',
      osmWayId: 768032824,
      floors: 4,
      roomCount: 0,
      aliases: ['landmark-hostel', 'Boys Hostel'],
      source: 'demo',
      createdAt: fixedDate
    },
    {
      blockId: 'CANTEEN',
      displayName: 'Canteen',
      nodeId: 'landmark-canteen',
      osmWayId: 355636593,
      floors: 2,
      roomCount: 0,
      aliases: ['landmark-canteen', 'Canteen'],
      source: 'demo',
      createdAt: fixedDate
    },
    {
      blockId: 'LIB',
      displayName: 'Central Library',
      nodeId: 'landmark-library',
      osmWayId: 355636605,
      floors: 3,
      roomCount: 0,
      aliases: ['landmark-library', 'Library'],
      source: 'demo',
      createdAt: fixedDate
    },
    {
      blockId: 'AUD',
      displayName: 'Auditorium',
      nodeId: 'landmark-auditorium',
      osmWayId: 355636577,
      floors: 2,
      roomCount: 0,
      aliases: ['landmark-auditorium', 'Auditorium'],
      source: 'demo',
      createdAt: fixedDate
    },
    {
      blockId: 'TNP',
      displayName: 'TNP Venue',
      nodeId: 'landmark-tnp',
      osmWayId: 355636490,
      floors: 2,
      roomCount: 0,
      aliases: ['landmark-tnp', 'TNP Venue'],
      source: 'demo',
      createdAt: fixedDate
    }
  ];

  const floors = [];
  const rooms = [];
  const equipment = [];

  // 1. Generate floors
  for (const b of blocks) {
    for (let f = 0; f < b.floors; f++) {
      floors.push({
        floorId: `${b.blockId}-F${f}`,
        blockId: b.blockId,
        floorNumber: f,
        displayName: f === 0 ? 'Ground Floor' : `Floor ${f}`,
        source: b.blockId === 'PG' && f === 0 ? 'srmeaswari.ac.in/mandatory-disclosure' : 'demo',
        createdAt: fixedDate
      });
    }
  }

  // 2. Generate rooms
  // PG Block: 17 rooms across 5 floors (4, 4, 3, 3, 3)
  const pgDistribution = [4, 4, 3, 3, 3];
  pgDistribution.forEach((count, f) => {
    for (let r = 1; r <= count; r++) {
      const roomNumStr = `${f}${String(r).padStart(2, '0')}`;
      const roomId = `PG-${roomNumStr}`;
      const isSmartLab = r === (f === 0 ? 1 : 2); // exactly ONE smart lab per floor
      const isA101 = f === 0 && r === 1;

      const roomRecord = {
        roomId,
        blockId: 'PG',
        floor: f,
        displayName: `PG ${roomNumStr}`,
        type: isSmartLab ? 'smart_lab' : (f === 0 ? 'lecture_hall' : 'classroom'),
        capacity: isA101 ? 60 : 64,
        nodeId: isA101 ? 'room-a101' : `node-${roomId.toLowerCase()}`,
        aliases: isA101 ? ['A101', 'room-a101', 'PG-A101', 'PG-001'] : [],
        hasEquipment: isSmartLab,
        source: 'srmeaswari.ac.in/mandatory-disclosure',
        createdAt: fixedDate
      };
      rooms.push(roomRecord);

      if (isSmartLab) {
        // Projector
        equipment.push({
          equipmentId: `${roomId}-PROJ`,
          roomId,
          blockId: 'PG',
          type: 'PROJECTOR',
          displayName: 'Ceiling Multimedia Projector',
          nodeId: isA101 ? 'projector-a101' : `equip-${roomId.toLowerCase()}-proj`,
          aliases: isA101 ? ['projector-a101'] : [],
          status: isA101 ? 'FAULTY' : 'OPERATIONAL',
          healthScore: isA101 ? 0.32 : 0.94,
          source: 'demo',
          createdAt: fixedDate
        });

        // AC Split Unit
        equipment.push({
          equipmentId: `${roomId}-AC`,
          roomId,
          blockId: 'PG',
          type: 'AC',
          displayName: '2.0 Ton Split Inverter AC',
          nodeId: `equip-${roomId.toLowerCase()}-ac`,
          aliases: [],
          status: 'OPERATIONAL',
          healthScore: 0.88,
          source: 'demo',
          createdAt: fixedDate
        });

        // Smart LED TV
        equipment.push({
          equipmentId: `${roomId}-TV`,
          roomId,
          blockId: 'PG',
          type: 'TV',
          displayName: '55" Ultra-HD Interactive Smart Display',
          nodeId: `equip-${roomId.toLowerCase()}-tv`,
          aliases: [],
          status: 'OPERATIONAL',
          healthScore: 0.96,
          source: 'demo',
          createdAt: fixedDate
        });
      }
    }
  });

  // Main Block: 41 rooms across 5 floors (8, 8, 9, 8, 8)
  const mainDistribution = [8, 8, 9, 8, 8];
  mainDistribution.forEach((count, f) => {
    for (let r = 1; r <= count; r++) {
      const roomNumStr = `${f}${String(r).padStart(2, '0')}`;
      const roomId = `MAIN-${roomNumStr}`;
      const isB204 = f === 2 && r === 4;

      rooms.push({
        roomId,
        blockId: 'MAIN',
        floor: f,
        displayName: `MAIN ${roomNumStr}`,
        type: isB204 ? 'lecture_hall' : 'classroom',
        capacity: isB204 ? 72 : 60,
        nodeId: isB204 ? 'room-b204' : `node-${roomId.toLowerCase()}`,
        aliases: isB204 ? ['B204', 'room-b204', 'MAIN-B204', 'MAIN-204'] : [],
        hasEquipment: false,
        source: 'srmeaswari.ac.in/mandatory-disclosure',
        createdAt: fixedDate
      });
    }
  });

  // Civil Block: 24 rooms across 4 floors (6, 6, 6, 6)
  const civilDistribution = [6, 6, 6, 6];
  civilDistribution.forEach((count, f) => {
    for (let r = 1; r <= count; r++) {
      const roomNumStr = `${f}${String(r).padStart(2, '0')}`;
      const roomId = `CIVIL-${roomNumStr}`;
      rooms.push({
        roomId,
        blockId: 'CIVIL',
        floor: f,
        displayName: `CIVIL ${roomNumStr}`,
        type: 'classroom',
        capacity: 60,
        nodeId: `node-${roomId.toLowerCase()}`,
        aliases: [],
        hasEquipment: false,
        source: 'srmeaswari.ac.in/mandatory-disclosure',
        createdAt: fixedDate
      });
    }
  });

  // Mechanical Block: 11 rooms across 3 floors (4, 4, 3)
  const mechDistribution = [4, 4, 3];
  mechDistribution.forEach((count, f) => {
    for (let r = 1; r <= count; r++) {
      const roomNumStr = `${f}${String(r).padStart(2, '0')}`;
      const roomId = `MECH-${roomNumStr}`;
      rooms.push({
        roomId,
        blockId: 'MECH',
        floor: f,
        displayName: `MECH ${roomNumStr}`,
        type: 'classroom',
        capacity: 60,
        nodeId: `node-${roomId.toLowerCase()}`,
        aliases: [],
        hasEquipment: false,
        source: 'srmeaswari.ac.in/mandatory-disclosure',
        createdAt: fixedDate
      });
    }
  });

  // Electronics Block: 10 rooms across 4 floors (3, 3, 2, 2)
  const eceDistribution = [3, 3, 2, 2];
  eceDistribution.forEach((count, f) => {
    for (let r = 1; r <= count; r++) {
      const roomNumStr = `${f}${String(r).padStart(2, '0')}`;
      const roomId = `ECE-${roomNumStr}`;
      rooms.push({
        roomId,
        blockId: 'ECE',
        floor: f,
        displayName: `ECE ${roomNumStr}`,
        type: 'classroom',
        capacity: 60,
        nodeId: `node-${roomId.toLowerCase()}`,
        aliases: [],
        hasEquipment: false,
        source: 'srmeaswari.ac.in/mandatory-disclosure',
        createdAt: fixedDate
      });
    }
  });

  const registry = {
    version: '1.0.0',
    campusId: 'srm-easwari-demo',
    campusName: 'SRM Easwari Engineering College',
    generatedAt: fixedDate,
    blocks,
    floors,
    rooms,
    equipment
  };

  fs.mkdirSync(path.dirname(targetPath), { recursive: true });
  fs.writeFileSync(targetPath, JSON.stringify(registry, null, 2), 'utf8');
  console.log(`Generated ${targetPath} successfully with ${blocks.length} blocks, ${floors.length} floors, ${rooms.length} rooms, and ${equipment.length} equipment items.`);
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  generateCampusRegistry(process.argv.includes('--force'));
}

