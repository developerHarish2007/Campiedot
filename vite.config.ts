import { defineConfig, type Plugin } from 'vite';
import react from '@vitejs/plugin-react';
import { existsSync, readFileSync, writeFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';

const assignmentsFile = fileURLToPath(new URL('./public/data/building-assignments.json', import.meta.url));
const adjustmentsFile = fileURLToPath(new URL('./public/data/facade-adjustments.json', import.meta.url));
const choices = new Set([
  'unassigned', 'not a campus building', 'Main Block', 'Electronics Block', 'Electronics Block I', 'Electronics Block II',
  'Basic Engineering Block', 'PG Block', 'Civil Block', 'Mechanical Block', 'Workshop Block 1', 'Workshop Block 2',
  'Workshop Block 3', 'East Block', 'Block 1', 'Block 2', 'Block 3', 'Block 4', 'Block 5', 'Block 6', 'Block 7',
  'Block 8', 'Block 9', 'Block 10', 'Block 11', 'Block 12', 'Block 13', 'Block 14',
  'Sports Complex', 'Boys Hostel', 'Canteen', 'Library', 'Auditorium', 'TNP Venue'
]);

function alignmentAssignments(): Plugin {
  return {
    name: 'campus-alignment-assignments',
    configureServer(server) {
      server.middlewares.use('/__alignment/assignments', (req, res, next) => {
        if (req.method === 'GET') {
          try { res.setHeader('Content-Type', 'application/json'); res.end(readFileSync(assignmentsFile)); }
          catch { res.statusCode = 404; res.end('{}'); }
          return;
        }
        if (req.method !== 'POST') { next(); return; }
        let body = '';
        req.on('data', chunk => { body += chunk; if (body.length > 65536) req.destroy(); });
        req.on('end', () => {
          try {
            const parsed: unknown = JSON.parse(body);
            if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) throw new Error('Expected an object');
            const valid = Object.fromEntries(Object.entries(parsed).filter(([id, name]) => /^\d+$/.test(id) && typeof name === 'string' && choices.has(name)));
            writeFileSync(assignmentsFile, `${JSON.stringify(valid, null, 2)}\n`, 'utf8');
            res.setHeader('Content-Type', 'application/json'); res.end(JSON.stringify({ ok: true, count: Object.keys(valid).length }));
          } catch { res.statusCode = 400; res.end('Invalid building assignments JSON'); }
        });
      });

      server.middlewares.use('/__facades/adjustments', (req, res, next) => {
        if (req.method === 'GET') {
          try {
            if (existsSync(adjustmentsFile)) {
              res.setHeader('Content-Type', 'application/json');
              res.end(readFileSync(adjustmentsFile));
              return;
            }
          } catch {}
          res.setHeader('Content-Type', 'application/json');
          res.end('{}');
          return;
        }
        if (req.method !== 'POST') { next(); return; }
        let body = '';
        req.on('data', chunk => { body += chunk; if (body.length > 65536) req.destroy(); });
        req.on('end', () => {
          try {
            const parsed: unknown = JSON.parse(body);
            if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) throw new Error('Expected an object');
            writeFileSync(adjustmentsFile, `${JSON.stringify(parsed, null, 2)}\n`, 'utf8');
            res.setHeader('Content-Type', 'application/json');
            res.end(JSON.stringify({ ok: true }));
          } catch {
            res.statusCode = 400;
            res.end('Invalid facade adjustments JSON');
          }
        });
      });
    }
  };
}

export default defineConfig({ plugins: [react(), alignmentAssignments()] });
