import { CanvasTexture, RepeatWrapping, SRGBColorSpace, Texture } from 'three';

let tileTexture: Texture | null = null;
let wallTexture: Texture | null = null;
let whiteboardTexture: Texture | null = null;
let noticeboardTexture: Texture | null = null;
let woodTexture: Texture | null = null;

/**
 * Procedural Vitrified Ceramic Tile (600x600 mm)
 * Light grey with delicate grey speckles and recessed dark grout lines.
 */
export function getTileTexture(): Texture {
  if (tileTexture) return tileTexture;

  const canvas = document.createElement('canvas');
  canvas.width = 1024;
  canvas.height = 1024;
  const ctx = canvas.getContext('2d');
  if (!ctx) return new Texture();

  // Base tile body: light institutional grey/beige
  ctx.fillStyle = '#dfdeda';
  ctx.fillRect(0, 0, 1024, 1024);

  // Subtle marble / vitrified speckling
  for (let i = 0; i < 18000; i++) {
    const x = Math.random() * 1024;
    const y = Math.random() * 1024;
    const s = Math.random() * 2.2 + 0.5;
    ctx.fillStyle = Math.random() > 0.5 ? 'rgba(255,255,255,0.45)' : 'rgba(180,175,168,0.35)';
    ctx.fillRect(x, y, s, s);
  }

  // 4x4 tile grid with 4mm grout lines
  ctx.lineWidth = 6;
  ctx.strokeStyle = '#9c978e';
  const tileSize = 256;
  for (let i = 0; i <= 1024; i += tileSize) {
    ctx.beginPath();
    ctx.moveTo(i, 0);
    ctx.lineTo(i, 1024);
    ctx.stroke();

    ctx.beginPath();
    ctx.moveTo(0, i);
    ctx.lineTo(1024, i);
    ctx.stroke();
  }

  // Grout inner shadow for depth
  ctx.lineWidth = 2;
  ctx.strokeStyle = '#7d786f';
  for (let i = 0; i <= 1024; i += tileSize) {
    ctx.beginPath();
    ctx.moveTo(i, 0);
    ctx.lineTo(i, 1024);
    ctx.stroke();

    ctx.beginPath();
    ctx.moveTo(0, i);
    ctx.lineTo(1024, i);
    ctx.stroke();
  }

  tileTexture = new CanvasTexture(canvas);
  tileTexture.wrapS = RepeatWrapping;
  tileTexture.wrapT = RepeatWrapping;
  tileTexture.colorSpace = SRGBColorSpace;
  tileTexture.repeat.set(3, 2.5);
  return tileTexture;
}

/**
 * Plastered Wall with classic Indian college Dado band:
 * Top: off-white matte plaster.
 * Bottom (approx 1.1m from floor): darker sage-grey/olive dado band with subtle scuffs.
 */
export function getWallTexture(): Texture {
  if (wallTexture) return wallTexture;

  const canvas = document.createElement('canvas');
  canvas.width = 1024;
  canvas.height = 1024;
  const ctx = canvas.getContext('2d');
  if (!ctx) return new Texture();

  // Top portion: warm off-white plaster
  ctx.fillStyle = '#f4f2ea';
  ctx.fillRect(0, 0, 1024, 680);

  // Subtle plaster grain
  for (let i = 0; i < 25000; i++) {
    const x = Math.random() * 1024;
    const y = Math.random() * 680;
    ctx.fillStyle = Math.random() > 0.5 ? 'rgba(255,255,255,0.3)' : 'rgba(210,205,195,0.2)';
    ctx.fillRect(x, y, 1.5, 1.5);
  }

  // Lower Dado band: classic Indian institutional olive-sage (#8c9485)
  ctx.fillStyle = '#8e9687';
  ctx.fillRect(0, 680, 1024, 344);

  // Dado top border line
  ctx.fillStyle = '#656d5e';
  ctx.fillRect(0, 676, 1024, 5);

  // Subtle scuffs and shoe marks near base
  for (let i = 0; i < 400; i++) {
    const x = Math.random() * 1024;
    const y = 690 + Math.random() * 320;
    const len = Math.random() * 18 + 4;
    ctx.fillStyle = 'rgba(70, 75, 66, 0.15)';
    ctx.fillRect(x, y, len, 2.2);
  }

  wallTexture = new CanvasTexture(canvas);
  wallTexture.wrapS = RepeatWrapping;
  wallTexture.wrapT = RepeatWrapping;
  wallTexture.colorSpace = SRGBColorSpace;
  return wallTexture;
}

/**
 * Whiteboard texture:
 * Clean white melamine surface with faint marker streaks and erased board residue.
 */
export function getWhiteboardTexture(): Texture {
  if (whiteboardTexture) return whiteboardTexture;

  const canvas = document.createElement('canvas');
  canvas.width = 1024;
  canvas.height = 512;
  const ctx = canvas.getContext('2d');
  if (!ctx) return new Texture();

  ctx.fillStyle = '#fdfdfd';
  ctx.fillRect(0, 0, 1024, 512);

  // Faint erased marker residue (subtle clouds)
  ctx.fillStyle = 'rgba(40, 80, 130, 0.025)';
  for (let i = 0; i < 15; i++) {
    ctx.beginPath();
    ctx.arc(100 + i * 60, 200 + Math.sin(i) * 50, 80, 0, Math.PI * 2);
    ctx.fill();
  }

  // Faint marker notes (engineering formulas / lecture diagram)
  ctx.fillStyle = 'rgba(20, 50, 100, 0.18)';
  ctx.font = '600 24px system-ui';
  ctx.fillText('ECE / CS · DIGITAL SYSTEMS', 80, 80);
  ctx.font = '500 18px monospace';
  ctx.fillText('f_clk = 100 MHz  |  T_prop <= 3.2 ns', 80, 120);
  ctx.fillText('FSM State Transition Matrix [S0 -> S1]', 80, 150);

  // Diagram box
  ctx.strokeStyle = 'rgba(30, 60, 120, 0.2)';
  ctx.lineWidth = 2.5;
  ctx.strokeRect(80, 180, 220, 140);
  ctx.fillText('ALU CORE', 130, 255);

  whiteboardTexture = new CanvasTexture(canvas);
  whiteboardTexture.colorSpace = SRGBColorSpace;
  return whiteboardTexture;
}

/**
 * Notice board:
 * Green felt corkboard with pinned circulars, timetable, and academic calendar.
 */
export function getNoticeBoardTexture(): Texture {
  if (noticeboardTexture) return noticeboardTexture;

  const canvas = document.createElement('canvas');
  canvas.width = 1024;
  canvas.height = 768;
  const ctx = canvas.getContext('2d');
  if (!ctx) return new Texture();

  // Green baize felt background
  ctx.fillStyle = '#2d5c3f';
  ctx.fillRect(0, 0, 1024, 768);

  // Felt texture noise
  for (let i = 0; i < 15000; i++) {
    ctx.fillStyle = Math.random() > 0.5 ? 'rgba(60,110,80,0.2)' : 'rgba(20,60,35,0.25)';
    ctx.fillRect(Math.random() * 1024, Math.random() * 768, 2, 2);
  }

  // Paper notice 1: Academic Schedule
  ctx.fillStyle = '#fffdfa';
  ctx.fillRect(50, 60, 280, 360);
  ctx.fillStyle = '#c53929';
  ctx.fillRect(50, 60, 280, 30);
  ctx.fillStyle = '#ffffff';
  ctx.font = 'bold 15px system-ui';
  ctx.fillText('ACADEMIC SCHEDULE 2026', 70, 82);
  ctx.fillStyle = '#333333';
  ctx.font = '11px system-ui';
  ctx.fillText('Internal Assessment II: Nov 10', 70, 130);
  ctx.fillText('Model Practical Exams: Nov 24', 70, 160);
  ctx.fillText('Anna University Exams: Dec 05', 70, 190);

  // Paper notice 2: Class Timetable
  ctx.fillStyle = '#f8f9fa';
  ctx.fillRect(380, 60, 320, 420);
  ctx.fillStyle = '#2c5282';
  ctx.fillRect(380, 60, 320, 30);
  ctx.fillStyle = '#ffffff';
  ctx.font = 'bold 15px system-ui';
  ctx.fillText('WEEKLY TIMETABLE - III YEAR', 400, 82);
  ctx.fillStyle = '#444444';
  ctx.font = '11px monospace';
  ctx.fillText('MON: DS Lab | OS | CN', 400, 130);
  ctx.fillText('TUE: Math IV | DBMS | AI', 400, 160);
  ctx.fillText('WED: Compiler | SE | MiniProj', 400, 190);
  ctx.fillText('THU: EmbedSys | Cloud | Aptitude', 400, 220);
  ctx.fillText('FRI: Library | Seminar | Mentor', 400, 250);

  // Paper notice 3: Smart Campus Guidelines
  ctx.fillStyle = '#fffef0';
  ctx.fillRect(740, 90, 230, 300);
  ctx.fillStyle = '#276749';
  ctx.font = 'bold 13px system-ui';
  ctx.fillText('SMART LAB NOTICE', 760, 125);
  ctx.fillStyle = '#444444';
  ctx.font = '10px system-ui';
  ctx.fillText('Switch off AC & Projector', 760, 155);
  ctx.fillText('after lecture conclusion.', 760, 175);
  ctx.fillText('Report hardware faults to', 760, 205);
  ctx.fillText('CampusOps Facilities desk.', 760, 225);

  // Pushpins
  const pins = [
    [190, 65, '#e53e3e'],
    [540, 65, '#3182ce'],
    [855, 95, '#d69e2e']
  ];
  pins.forEach(([px, py, col]) => {
    ctx.fillStyle = col as string;
    ctx.beginPath();
    ctx.arc(px as number, py as number, 8, 0, Math.PI * 2);
    ctx.fill();
    ctx.strokeStyle = '#ffffff';
    ctx.lineWidth = 2;
    ctx.stroke();
  });

  noticeboardTexture = new CanvasTexture(canvas);
  noticeboardTexture.colorSpace = SRGBColorSpace;
  return noticeboardTexture;
}

/**
 * Natural teak wood laminate texture for classroom bench tops and solid doors.
 */
export function getWoodTexture(): Texture {
  if (woodTexture) return woodTexture;

  const canvas = document.createElement('canvas');
  canvas.width = 512;
  canvas.height = 512;
  const ctx = canvas.getContext('2d');
  if (!ctx) return new Texture();

  ctx.fillStyle = '#b77b47';
  ctx.fillRect(0, 0, 512, 512);

  // Directional wood grain
  for (let y = 0; y < 512; y += 3) {
    const alpha = Math.sin(y * 0.08) * 0.12 + Math.random() * 0.08;
    ctx.fillStyle = `rgba(110, 60, 25, ${alpha + 0.1})`;
    ctx.fillRect(0, y, 512, Math.random() * 3 + 1);
  }

  woodTexture = new CanvasTexture(canvas);
  woodTexture.wrapS = RepeatWrapping;
  woodTexture.wrapT = RepeatWrapping;
  woodTexture.colorSpace = SRGBColorSpace;
  return woodTexture;
}

export function disposeClassroomTextures() {
  tileTexture?.dispose();
  wallTexture?.dispose();
  whiteboardTexture?.dispose();
  noticeboardTexture?.dispose();
  woodTexture?.dispose();
  tileTexture = null;
  wallTexture = null;
  whiteboardTexture = null;
  noticeboardTexture = null;
  woodTexture = null;
}

