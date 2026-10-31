const fs = require('fs');
const path = './src/data/registry/campusRegistry.json';
const data = JSON.parse(fs.readFileSync(path, 'utf8'));

// 1. Update blocks source
data.blocks.forEach(b => {
  if (b.source === 'srmeaswari.ac.in/mandatory-disclosure') b.source = 'demo';
});

// 2. Update rooms
data.rooms.forEach(r => {
  if (r.source === 'srmeaswari.ac.in/mandatory-disclosure') r.source = 'demo';
  if (r.roomId === 'PG-001') {
    r.type = 'lecture_hall';
    r.hasEquipment = false;
  }
  if (r.roomId === 'PG-101') {
    r.type = 'classroom';
    r.hasEquipment = false;
  }
  if (r.roomId === 'PG-201') {
    r.type = 'smart_lab';
    r.hasEquipment = true;
  }
});

// 3. Update equipment
data.equipment = data.equipment.filter(e => e.roomId !== 'PG-001');

// Ensure PG-201 has equipment
const hasPg201 = data.equipment.some(e => e.roomId === 'PG-201');
if (!hasPg201) {
  data.equipment.unshift(
    {
      equipmentId: 'PG-201-PROJ',
      roomId: 'PG-201',
      blockId: 'PG',
      type: 'PROJECTOR',
      displayName: 'Ceiling Multimedia Projector',
      nodeId: 'equip-pg-201-proj',
      aliases: [],
      status: 'OPERATIONAL',
      healthScore: 0.94,
      source: 'demo',
      createdAt: '2026-10-31T00:00:00Z'
    },
    {
      equipmentId: 'PG-201-AC',
      roomId: 'PG-201',
      blockId: 'PG',
      type: 'AC',
      displayName: '2.0 Ton Split Inverter AC',
      nodeId: 'equip-pg-201-ac',
      aliases: [],
      status: 'OPERATIONAL',
      healthScore: 0.88,
      source: 'demo',
      createdAt: '2026-10-31T00:00:00Z'
    },
    {
      equipmentId: 'PG-201-TV',
      roomId: 'PG-201',
      blockId: 'PG',
      type: 'TV',
      displayName: '55" Ultra-HD Interactive Smart Display',
      nodeId: 'equip-pg-201-tv',
      aliases: [],
      status: 'OPERATIONAL',
      healthScore: 0.96,
      source: 'demo',
      createdAt: '2026-10-31T00:00:00Z'
    }
  );
}

fs.writeFileSync(path, JSON.stringify(data, null, 2), 'utf8');
console.log('Updated campusRegistry.json successfully!');
