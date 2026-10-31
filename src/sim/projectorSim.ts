// PJLink-style Projector Telemetry Simulator
// Seeded repeatable PRNG

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

// Assumed engineering constants
export const RATED_LAMP_HOURS = 3000; // ASSUMED: typical educational DLP/LCD lamp life
export const FILTER_SERVICE_INTERVAL = 500; // ASSUMED: recommended cleaning interval

export const PG_PROJECTOR_IDS = [
  { deviceId: 'PG-102-PROJ', roomId: 'PG-102', baseLampHours: 1480, baseFilterHours: 210 },
  { deviceId: 'PG-201-PROJ', roomId: 'PG-201', baseLampHours: 2740, baseFilterHours: 420 }, // near end of life
  { deviceId: 'PG-202-PROJ', roomId: 'PG-202', baseLampHours: 720, baseFilterHours: 110 },
  { deviceId: 'PG-302-PROJ', roomId: 'PG-302', baseLampHours: 390, baseFilterHours: 85 },
  { deviceId: 'PG-402-PROJ', roomId: 'PG-402', baseLampHours: 1050, baseFilterHours: 310 }
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

  constructor() {
    this.reset();
  }

  public reset() {
    this.faults = {
      'PG-102-PROJ': { faultType: 'none', injectedAtDay: 0 },
      'PG-201-PROJ': { faultType: 'none', injectedAtDay: 0 },
      'PG-202-PROJ': { faultType: 'none', injectedAtDay: 0 },
      'PG-302-PROJ': { faultType: 'none', injectedAtDay: 0 },
      'PG-402-PROJ': { faultType: 'none', injectedAtDay: 0 }
    };
  }

  public setFault(deviceId: string, faultType: FaultType, currentDay: number) {
    this.faults[deviceId] = { faultType, injectedAtDay: currentDay };
  }

  public getFault(deviceId: string): FaultType {
    return this.faults[deviceId]?.faultType ?? 'none';
  }

  // Returns all daily readings up to `targetDay` (0..30)
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
      // Missing reading simulation (e.g. network dropout ~4% chance, except day 0 or current day)
      const isMissing = day > 0 && day < targetDay && rng() < 0.05;

      // Normal daily accumulation: ~6.0 hours/day with ±0.5h noise
      const dailyUse = 5.6 + rng() * 0.9;
      lampHours += dailyUse;
      filterHours += dailyUse;

      // Fault injection logic
      const isFaulted = fault.faultType !== 'none' && day >= fault.injectedAtDay;
      const daysSinceFault = day - fault.injectedAtDay;

      const flags: PJLinkFlags = {
        fan: 'ok',
        lamp: 'ok',
        temperature: 'ok',
        cover: 'ok',
        filter: 'ok',
        other: 'ok'
      };

      if (isFaulted) {
        if (fault.faultType === 'lamp_wear') {
          // Jump to 92% rated life + daily wear
          const jumpHours = Math.max(lampHours, RATED_LAMP_HOURS * 0.92 + daysSinceFault * 6);
          lampHours = jumpHours;
          flags.lamp = lampHours >= RATED_LAMP_HOURS ? 'error' : 'warning';
        } else if (fault.faultType === 'dirty_filter') {
          filterHours = Math.max(filterHours, FILTER_SERVICE_INTERVAL + 45 + daysSinceFault * 8);
          flags.filter = 'warning';
          // ASSUMED: dirty filter causes temperature warning after 2 days, error after 5 days
          if (daysSinceFault >= 5) {
            flags.temperature = 'error';
          } else if (daysSinceFault >= 2) {
            flags.temperature = 'warning';
          }
        } else if (fault.faultType === 'fan_fault') {
          // ASSUMED: fan degradation warning immediately, error after 3 days
          if (daysSinceFault >= 3) {
            flags.fan = 'error';
            flags.temperature = 'error';
          } else {
            flags.fan = 'warning';
          }
        }
      } else {
        // Natural wear thresholds
        if (lampHours >= RATED_LAMP_HOURS) {
          flags.lamp = 'error';
        } else if (lampHours >= RATED_LAMP_HOURS * 0.90) {
          flags.lamp = 'warning';
        }

        if (filterHours >= FILTER_SERVICE_INTERVAL) {
          flags.filter = 'warning';
        }
      }

      readings.push({
        deviceId,
        roomId: config.roomId,
        day,
        timestamp: new Date(Date.now() + (day - targetDay) * 86400000).toISOString(),
        lampHours: Math.round(lampHours * 10) / 10,
        filterHours: Math.round(filterHours * 10) / 10,
        flags,
        missing: isMissing
      });
    }

    return readings;
  }
}

// Global simulator singleton for state preservation
export const projectorSim = new ProjectorSimulator();
