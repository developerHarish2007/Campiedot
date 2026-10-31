// PJLink-style Projector Telemetry Simulator
// Deterministic Scripted Pilot Scenario + Configurable Fault Injection

export type FlagStatus = 'ok' | 'warning' | 'error';

export interface PJLinkFlags {
  fan: FlagStatus;
  lamp: FlagStatus;
  temperature: FlagStatus;
  cover: FlagStatus;
  filter: FlagStatus;
  other: FlagStatus;
}

export interface ProjectorReading {
  deviceId: string;
  roomId: string;
  day: number;
  timestamp: string;
  lampHours: number;
  filterHours: number;
  flags: PJLinkFlags;
  missing?: boolean;
}

export type FaultType = 'none' | 'lamp_wear' | 'dirty_filter' | 'fan_fault';

export interface ProjectorFaultConfig {
  faultType: FaultType;
  injectedAtDay: number;
}

export interface ProjectorConfig {
  deviceId: string;
  roomId: string;
  floor: number;
  floorName: string;
  baseLampHours: number;
  baseFilterHours: number;
  ip: string;
}

// Assumed engineering constants
export const RATED_LAMP_HOURS = 3000; // ASSUMED: educational DLP/LCD lamp rated life
export const FILTER_SERVICE_INTERVAL = 500; // ASSUMED: recommended cleaning interval
export const DAILY_LAMP_HOURS = 6.0; // ASSUMED: exact scheduled daily operation hours
export const BASE_SIM_DATE = '2026-10-31'; // Scripted baseline calendar date

// 5 Smart Labs, one projector each (floors 0 to 4)
export const PG_PROJECTOR_IDS: ProjectorConfig[] = [
  { deviceId: 'PG-001-PROJ', roomId: 'PG-001', floor: 0, floorName: 'Floor 0 (PG-001)', baseLampHours: 600, baseFilterHours: 100, ip: '10.14.0.12' },
  { deviceId: 'PG-102-PROJ', roomId: 'PG-102', floor: 1, floorName: 'Floor 1 (PG-102)', baseLampHours: 1500, baseFilterHours: 150, ip: '10.14.1.25' },
  { deviceId: 'PG-201-PROJ', roomId: 'PG-201', floor: 2, floorName: 'Floor 2 (PG-201)', baseLampHours: 2790, baseFilterHours: 200, ip: '10.14.2.10' },
  { deviceId: 'PG-302-PROJ', roomId: 'PG-302', floor: 3, floorName: 'Floor 3 (PG-302)', baseLampHours: 800, baseFilterHours: 120, ip: '10.14.3.42' },
  { deviceId: 'PG-402-PROJ', roomId: 'PG-402', floor: 4, floorName: 'Floor 4 (PG-402)', baseLampHours: 1100, baseFilterHours: 350, ip: '10.14.4.18' }
];

function mulberry32(seed: number) {
  return function() {
    let t = (seed += 0x6d2b79f5);
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

export class ProjectorSimulator {
  private faults: Record<string, ProjectorFaultConfig> = {};
  public noiseEnabled: boolean = false; // Default OFF for full determinism

  constructor() {
    this.reset();
  }

  public reset() {
    this.faults = {};
    for (const p of PG_PROJECTOR_IDS) {
      this.faults[p.deviceId] = { faultType: 'none', injectedAtDay: 0 };
    }
  }

  public setFault(deviceId: string, faultType: FaultType, currentDay: number) {
    this.faults[deviceId] = { faultType, injectedAtDay: currentDay };
  }

  public getFault(deviceId: string): FaultType {
    return this.faults[deviceId]?.faultType ?? 'none';
  }

  public setNoiseEnabled(enabled: boolean) {
    this.noiseEnabled = enabled;
  }

  // Returns all daily readings up to targetDay (0..30)
  public getReadingsUpToDay(deviceId: string, targetDay: number): ProjectorReading[] {
    const config = PG_PROJECTOR_IDS.find(p => p.deviceId === deviceId);
    if (!config) return [];

    const fault = this.faults[deviceId] ?? { faultType: 'none', injectedAtDay: 0 };
    const readings: ProjectorReading[] = [];
    const seed = deviceId.split('').reduce((acc, c) => acc + c.charCodeAt(0), 101);
    const rng = mulberry32(seed);

    let lampHours = config.baseLampHours;
    let filterHours = config.baseFilterHours;

    for (let day = 0; day <= targetDay; day++) {
      // 1. Packet dropouts ONLY if noiseEnabled is true
      const isMissing = this.noiseEnabled && day > 0 && day < targetDay && rng() < 0.05;

      // 2. Daily accumulation: exactly 6.0 h/day when deterministic
      let dailyUse = DAILY_LAMP_HOURS;
      if (this.noiseEnabled) {
        dailyUse = 5.7 + rng() * 0.6; // subtle ±0.3h jitter
      }

      if (day > 0) {
        lampHours += dailyUse;
        filterHours += dailyUse;
      }

      // 3. Flags and State Computation (Pilot scripted scenario or user injected fault)
      const flags: PJLinkFlags = {
        fan: 'ok',
        lamp: 'ok',
        temperature: 'ok',
        cover: 'ok',
        filter: 'ok',
        other: 'ok'
      };

      // User manual fault overrides
      if (fault.faultType === 'lamp_wear' && day >= fault.injectedAtDay) {
        if (day === fault.injectedAtDay) {
          lampHours = Math.max(lampHours, 2760);
        }
      } else if (fault.faultType === 'dirty_filter' && day >= fault.injectedAtDay) {
        if (day === fault.injectedAtDay) {
          filterHours = Math.max(filterHours, 510);
        }
        flags.filter = 'warning';
        const daysInFault = day - fault.injectedAtDay;
        if (daysInFault >= 10) {
          flags.temperature = 'error';
        } else {
          flags.temperature = 'warning';
        }
      } else if (fault.faultType === 'fan_fault' && day >= fault.injectedAtDay) {
        const daysInFault = day - fault.injectedAtDay;
        if (daysInFault >= 10) {
          flags.fan = 'error';
        } else {
          flags.fan = 'warning';
        }
      } else {
        // DEFAULT SCRIPTED PILOT DEMO SCENARIO
        if (deviceId === 'PG-201-PROJ') {
          // Floor 2: lamp end of life. Lamp reaches 3000h at day 35.
          // Optional lamp warning flag at day 14 (<= 21 days)
          if (lampHours >= RATED_LAMP_HOURS) {
            flags.lamp = 'error';
          } else if (day >= 14) {
            flags.lamp = 'warning';
          }
        } else if (deviceId === 'PG-302-PROJ') {
          // Floor 3: fan fault. Healthy until day 11. Day 12 warning, day 22 error (10 days later).
          if (day >= 22) {
            flags.fan = 'error';
          } else if (day >= 12) {
            flags.fan = 'warning';
          }
        } else if (deviceId === 'PG-402-PROJ') {
          // Floor 4: dirty filter. Filter crosses 500h at day 25 -> temp warning, error 10 days later (day 35).
          if (filterHours >= FILTER_SERVICE_INTERVAL) {
            flags.filter = 'warning';
          }
          if (day >= 35) {
            flags.temperature = 'error';
          } else if (day >= 25) {
            flags.temperature = 'warning';
          }
        }
      }

      // Check lamp hard limit
      if (lampHours >= RATED_LAMP_HOURS) {
        flags.lamp = 'error';
      }

      // Timestamp calculation
      const d = new Date(new Date(BASE_SIM_DATE + 'T09:00:00Z').getTime() + day * 86400000);
      const timestamp = d.toISOString();

      readings.push({
        deviceId,
        roomId: config.roomId,
        day,
        timestamp,
        lampHours: Math.round(lampHours * 10) / 10,
        filterHours: Math.round(filterHours * 10) / 10,
        flags,
        missing: isMissing
      });
    }

    return readings;
  }

  // Generates 8 real-time PJLink query/response pairs + JSON telemetry payload
  public getPJLinkExchanges(deviceId: string, reading: ProjectorReading): { exchanges: Array<{ cmd: string; resp: string; desc: string }>; jsonPayload: any } {
    const config = PG_PROJECTOR_IDS.find(p => p.deviceId === deviceId);
    const ip = config?.ip ?? '10.14.2.10';

    const flagCode = (f: FlagStatus) => (f === 'ok' ? '0' : f === 'warning' ? '1' : '2');
    const fanCode = flagCode(reading.flags.fan);
    const lampCode = flagCode(reading.flags.lamp);
    const tempCode = flagCode(reading.flags.temperature);
    const covCode = flagCode(reading.flags.cover);
    const filtCode = flagCode(reading.flags.filter);
    const othCode = flagCode(reading.flags.other);

    const exchanges = [
      { cmd: '%1POWR ?\\r', resp: '%1POWR=1', desc: 'Power state query -> Power ON' },
      { cmd: '%1INPT ?\\r', resp: '%1INPT=31', desc: 'Active video input query -> HDMI 1 (Digital)' },
      { cmd: '%1LAMP ?\\r', resp: `%1LAMP=${Math.round(reading.lampHours)} 1`, desc: `Lamp hours query -> ${Math.round(reading.lampHours)} h (Lamp ON)` },
      { cmd: '%1ERST ?\\r', resp: `%1ERST=${fanCode}${lampCode}${tempCode}${covCode}${filtCode}${othCode}`, desc: `Error status query -> Fan:${fanCode} Lamp:${lampCode} Temp:${tempCode} Cover:${covCode} Filter:${filtCode} Other:${othCode}` },
      { cmd: '%1NAME ?\\r', resp: `%1NAME=PG-SmartLab-${reading.roomId}`, desc: `Projector network name -> PG-SmartLab-${reading.roomId}` },
      { cmd: '%1INF1 ?\\r', resp: '%1INF1=EPSON EB-L630U WUXGA', desc: 'Manufacturer & model query -> Epson EB-L630U' },
      { cmd: '%1INF2 ?\\r', resp: '%1INF2=PJLink_v2.00_Compliant', desc: 'PJLink protocol specification version -> Class 2 v2.00' },
      { cmd: '%2FILT ?\\r', resp: `%2FILT=${Math.round(reading.filterHours)}`, desc: `Filter timer query -> ${Math.round(reading.filterHours)} h` }
    ];

    const jsonPayload = {
      deviceId: reading.deviceId,
      roomId: reading.roomId,
      hostIp: `${ip}:4352`,
      gatewayHost: '10.14.0.1 (Campus Gateway Agent)',
      pollIntervalSeconds: 60,
      protocol: 'PJLink Class 2 (TCP/IP)',
      timestamp: reading.timestamp,
      telemetry: {
        lampHours: reading.lampHours,
        ratedLampHours: RATED_LAMP_HOURS,
        filterHours: reading.filterHours,
        filterInterval: FILTER_SERVICE_INTERVAL,
        flags: reading.flags
      }
    };

    return { exchanges, jsonPayload };
  }
}

export const projectorSim = new ProjectorSimulator();
