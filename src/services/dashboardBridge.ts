// Bridge connecting Arun0729 CampusOps Dashboard and Antigravity 3D Digital Twin
import roomMappingRaw from '../data/roomMapping.json';
import { DevicePrediction } from '../sim/projectorPredictor';

export interface StudentReport {
  id: string;
  ticketNumber: number;
  room: string; // Dashboard room code (e.g. "A101" or "PG-201")
  mappedRoomId: string; // Twin registry room ID (e.g. "PG-001" or "PG-201")
  category: string;
  description: string;
  state: 'OPEN' | 'IN_PROGRESS' | 'RESOLVED' | 'REJECTED';
  reporterUrgency: string;
  createdAt: string;
  simulated?: boolean;
}

export interface PredictiveWarningPayload {
  id: string;
  source: 'predictive';
  severity: 'warning';
  room: string;
  deviceId: string;
  failureMode: string;
  predictedFailureAt: string;
  reasons: string[];
  workerRole: 'av_technician' | 'electrician';
  raw_description: string;
  createdAt: string;
}

export interface LastWarningNotification {
  id: string;
  time: string;
  status: 'sent' | 'fallback_outbox' | 'error';
  message: string;
  payload: PredictiveWarningPayload;
}

const roomMapping: Record<string, string> = roomMappingRaw as Record<string, string>;

// Reverse mapping: ourRoomId -> theirCode
const reverseRoomMapping: Record<string, string> = {};
for (const [theirCode, ourId] of Object.entries(roomMapping)) {
  if (!reverseRoomMapping[ourId]) {
    reverseRoomMapping[ourId] = theirCode;
  }
}

export class DashboardBridge {
  private reports: StudentReport[] = [];
  private lastTransitions: Record<string, string> = {}; // deviceId -> previous healthState
  private lastWarningNotice: LastWarningNotification | null = null;
  private listeners: Set<() => void> = new Set();
  private pollTimer: any = null;

  constructor() {
    this.loadFromStorage();
    this.startPolling();
  }

  public subscribe(fn: () => void) {
    this.listeners.add(fn);
    return () => {
      this.listeners.delete(fn);
    };
  }

  private notify() {
    this.listeners.forEach(fn => fn());
  }

  public toOurRoomId(theirCode: string): string {
    if (!theirCode) return '';
    const clean = theirCode.trim();
    if (roomMapping[clean]) {
      return roomMapping[clean];
    }
    // Check uppercase or case insensitive
    const found = Object.keys(roomMapping).find(k => k.toLowerCase() === clean.toLowerCase());
    if (found) {
      return roomMapping[found];
    }
    console.warn(`[dashboardBridge] Unmatched room identifier from report: "${theirCode}"`);
    return theirCode;
  }

  public toTheirRoomId(ourRoomId: string): string {
    return reverseRoomMapping[ourRoomId] ?? ourRoomId;
  }

  private loadFromStorage() {
    try {
      if (typeof window !== 'undefined') {
        const raw = localStorage.getItem('campusops_bridge_reports');
        if (raw) {
          this.reports = JSON.parse(raw);
        }
        const lastNotice = localStorage.getItem('campusops_bridge_last_warning');
        if (lastNotice) {
          this.lastWarningNotice = JSON.parse(lastNotice);
        }
      }
    } catch (e) {
      console.warn('[dashboardBridge] Failed to load local reports store', e);
    }
  }

  private saveToStorage() {
    try {
      if (typeof window !== 'undefined') {
        localStorage.setItem('campusops_bridge_reports', JSON.stringify(this.reports));
        if (this.lastWarningNotice) {
          localStorage.setItem('campusops_bridge_last_warning', JSON.stringify(this.lastWarningNotice));
        }
      }
    } catch {
      /* ignore storage errors */
    }
  }

  // Polls dashboard backend / work-orders API every 5s if available
  private startPolling() {
    if (typeof window === 'undefined') return;
    this.pollTimer = setInterval(async () => {
      try {
        let res: Response | null = null;
        try {
          res = await fetch('http://localhost:5173/api/v1/work-orders?limit=25', {
            headers: { 'Content-Type': 'application/json' }
          });
        } catch {}
        if (!res || !res.ok) {
          try {
            res = await fetch('http://localhost:8000/api/v1/work-orders?limit=25', {
              headers: { 'Content-Type': 'application/json' }
            });
          } catch {}
        }
        if (res && res.ok) {
          const data = await res.json();
          if (Array.isArray(data)) {
            let changed = false;
            for (const item of data) {
              const theirRoom = item.node_code || item.node_name || '';
              const ourRoom = this.toOurRoomId(theirRoom);
              const existingIdx = this.reports.findIndex(r => r.id === String(item.id || item.ticket_number));
              const reportState = ['RESOLVED', 'REJECTED', 'CLOSED'].includes(item.state) ? 'RESOLVED' : 'OPEN';
              const repObj: StudentReport = {
                id: String(item.id || item.ticket_number),
                ticketNumber: item.ticket_number || 100,
                room: theirRoom,
                mappedRoomId: ourRoom,
                category: item.category || 'GENERAL',
                description: item.raw_description || item.ai_summary || '',
                state: reportState,
                reporterUrgency: item.reporter_urgency || 'P2_MEDIUM',
                createdAt: item.created_at || new Date().toISOString(),
                simulated: false
              };
              if (existingIdx >= 0) {
                if (this.reports[existingIdx].state !== reportState) {
                  this.reports[existingIdx] = repObj;
                  changed = true;
                }
              } else {
                this.reports.unshift(repObj);
                changed = true;
              }
            }
            if (changed) {
              this.saveToStorage();
              this.notify();
            }
          }
        }
      } catch {
        // Backend not listening on 8000 (FALLBACK mode active)
      }
    }, 5000);
  }

  // -------------------------------------------------------------
  // ARROW 1: Student Reports State Access
  // -------------------------------------------------------------

  public getAllReports(): StudentReport[] {
    return this.reports;
  }

  public getOpenReportsForRoom(roomId: string): StudentReport[] {
    const ourId = this.toOurRoomId(roomId);
    return this.reports.filter(r => r.state === 'OPEN' && (r.mappedRoomId === ourId || r.room === roomId));
  }

  public hasOpenReport(roomId: string): boolean {
    return this.getOpenReportsForRoom(roomId).length > 0;
  }

  public getOpenReportCount(roomId: string): number {
    return this.getOpenReportsForRoom(roomId).length;
  }

  public buildingHasOpenReports(blockId: string): boolean {
    return this.reports.some(r => r.state === 'OPEN' && r.mappedRoomId.startsWith(`${blockId}-`));
  }

  // Dev Button: Simulate student report (FALLBACK & live testing)
  public simulateStudentReport(roomId: string, category = 'AV', desc?: string): StudentReport {
    const theirRoom = this.toTheirRoomId(roomId);
    const id = `report_sim_${Date.now()}_${Math.floor(Math.random() * 1000)}`;
    const ticketNumber = Math.floor(1000 + Math.random() * 9000);
    const newReport: StudentReport = {
      id,
      ticketNumber,
      room: theirRoom,
      mappedRoomId: roomId,
      category,
      description: desc ?? `[Simulated Student Report] Projector image flickering and loud cooling fan noise in room ${theirRoom}`,
      state: 'OPEN',
      reporterUrgency: 'P1_HIGH',
      createdAt: new Date().toISOString(),
      simulated: true
    };

    this.reports.unshift(newReport);
    this.saveToStorage();
    this.notify();
    return newReport;
  }

  public resolveReportsForRoom(roomId: string) {
    const ourId = this.toOurRoomId(roomId);
    let changed = false;
    this.reports.forEach(r => {
      if ((r.mappedRoomId === ourId || r.room === roomId) && r.state === 'OPEN') {
        r.state = 'RESOLVED';
        changed = true;
      }
    });
    if (changed) {
      this.saveToStorage();
      this.notify();
    }
  }

  public clearAllSimulatedReports() {
    this.reports = this.reports.filter(r => !r.simulated);
    this.saveToStorage();
    this.notify();
  }

  // -------------------------------------------------------------
  // ARROW 2: Projector Predictive Warning Integration
  // -------------------------------------------------------------

  public checkAndDispatchPrediction(pred: DevicePrediction) {
    const prev = this.lastTransitions[pred.deviceId];
    const curr = pred.healthState;

    // Transition ONLY (never every tick)
    if (prev === curr) return;
    this.lastTransitions[pred.deviceId] = curr;

    // Trigger on transition to degrading or imminent
    if (curr === 'degrading' || curr === 'imminent') {
      this.dispatchWarning(pred);
    }
  }

  private async dispatchWarning(pred: DevicePrediction) {
    const theirRoom = this.toTheirRoomId(pred.roomId);
    const stableId = `pred_${pred.deviceId}_${pred.failureMode}`;
    const timestamp = new Date().toLocaleTimeString();

    const payload: PredictiveWarningPayload = {
      id: stableId,
      source: 'predictive',
      severity: 'warning',
      room: theirRoom,
      deviceId: pred.deviceId,
      failureMode: pred.failureMode,
      predictedFailureAt: pred.predictedFailureAt,
      reasons: pred.reasons,
      workerRole: 'av_technician',
      raw_description: `[AUTOMATED PREDICTIVE WARNING] ${pred.reasons[0]} (Scheduled Failure: ${pred.predictedFailureAt})`,
      createdAt: new Date().toISOString()
    };

    let sentViaApi = false;
    let errorMsg = '';

    // Attempt 1: POST to dashboard backend work orders intake
    try {
      const res = await fetch('http://localhost:8000/api/v1/work-orders', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          raw_description: payload.raw_description,
          category: 'AV',
          reporter_urgency: pred.healthState === 'imminent' ? 'P1_HIGH' : 'P2_MEDIUM',
          ai_summary: pred.drivingReason,
          initial_state: 'INGESTED'
        })
      });
      if (res.ok) {
        sentViaApi = true;
      }
    } catch (e: any) {
      errorMsg = e?.message || 'Connection refused (localhost:8000)';
    }

    // Attempt 2 (FALLBACK): Save to dashboard/outbox/warnings.json via endpoint & client state / localStorage
    try {
      await fetch('/__dashboard/outbox', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
    } catch {}

    this.lastWarningNotice = {
      id: stableId,
      time: timestamp,
      status: sentViaApi ? 'sent' : 'fallback_outbox',
      message: sentViaApi
        ? `Warning sent to dashboard: ${stableId}, ${timestamp}`
        : `Warning sent to dashboard outbox: ${stableId}, ${timestamp}`,
      payload
    };

    this.saveToStorage();
    this.notify();
    console.log(`[dashboardBridge] ${this.lastWarningNotice.message}`);
  }

  public getLastWarningNotice(): LastWarningNotification | null {
    return this.lastWarningNotice;
  }
}

export const dashboardBridge = new DashboardBridge();
if (typeof window !== 'undefined') {
  (window as any).dashboardBridge = dashboardBridge;
}
