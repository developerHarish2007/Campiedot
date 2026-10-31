// Deterministic Projector Predictive Maintenance Model (Rules + Trend)
import {
  ProjectorReading,
  RATED_LAMP_HOURS,
  FILTER_SERVICE_INTERVAL
} from './projectorSim';

export type HealthState = 'healthy' | 'degrading' | 'imminent' | 'failed';
export type Confidence = 'low' | 'medium' | 'high';
export type FailureMode = 'lamp_end_of_life' | 'filter_overheat' | 'fan_fault' | 'none';

export interface DevicePrediction {
  deviceId: string;
  roomId: string;
  healthScore: number; // 0..100
  healthState: HealthState;
  predictedFailureAt: string | null;
  daysRemaining: number | null;
  confidence: Confidence;
  failureMode: FailureMode;
  reasons: string[];
  lastReading: ProjectorReading | null;
}

export class ProjectorPredictor {
  // Evaluates device health from time series readings
  public predict(deviceId: string, readings: ProjectorReading[]): DevicePrediction {
    const validReadings = readings.filter(r => !r.missing);
    const lastReading = validReadings.length > 0 ? validReadings[validReadings.length - 1] : null;

    if (!lastReading) {
      return {
        deviceId,
        roomId: '',
        healthScore: 100,
        healthState: 'healthy',
        predictedFailureAt: null,
        daysRemaining: null,
        confidence: 'low',
        failureMode: 'none',
        reasons: ['No telemetry readings available'],
        lastReading: null
      };
    }

    const reasons: string[] = [];
    let healthScore = 100;
    let failureMode: FailureMode = 'none';
    let confidence: Confidence = 'high';

    // 1. Calculate 7-day average daily usage rate
    const recent = validReadings.slice(-8);
    let avgHoursPerDay = 6.0; // fallback standard 6h/day
    if (recent.length >= 2) {
      const first = recent[0];
      const last = recent[recent.length - 1];
      const deltaDays = Math.max(1, last.day - first.day);
      const deltaHours = Math.max(0.1, last.lampHours - first.lampHours);
      avgHoursPerDay = Math.max(1.0, Math.min(14.0, deltaHours / deltaDays));
    }

    // Check for missing readings in window
    const missingCount = readings.slice(-7).filter(r => r.missing).length;
    if (missingCount >= 2) {
      confidence = 'low';
      reasons.push(`${missingCount} telemetry packets dropped in the last 7 days`);
    } else if (missingCount === 1) {
      confidence = 'medium';
    }

    // 2. Lamp life degradation (Trend component)
    const remainingLampHours = Math.max(0, RATED_LAMP_HOURS - lastReading.lampHours);
    const lampWearRatio = lastReading.lampHours / RATED_LAMP_HOURS;
    const estDaysRemaining = Math.max(0, Math.round(remainingLampHours / avgHoursPerDay));

    if (lampWearRatio >= 1.0) {
      healthScore = 0;
      failureMode = 'lamp_end_of_life';
      reasons.push(`Lamp expired (${lastReading.lampHours}/${RATED_LAMP_HOURS} h)`);
    } else if (lampWearRatio >= 0.90) {
      healthScore = Math.min(healthScore, 35);
      failureMode = 'lamp_end_of_life';
      reasons.push(`Lamp at ${Math.round(lampWearRatio * 100)}% rated life (${lastReading.lampHours}/${RATED_LAMP_HOURS} h), ~${estDaysRemaining} days left at ${avgHoursPerDay.toFixed(1)} h/day`);
    } else if (lampWearRatio >= 0.75) {
      healthScore = Math.min(healthScore, 70);
      reasons.push(`Lamp wear normal (${lastReading.lampHours}/${RATED_LAMP_HOURS} h), ~${estDaysRemaining} days remaining`);
    } else {
      reasons.push(`Lamp healthy (${lastReading.lampHours}/${RATED_LAMP_HOURS} h)`);
    }

    // 3. Filter check
    if (lastReading.filterHours >= FILTER_SERVICE_INTERVAL) {
      healthScore = Math.min(healthScore, healthScore - 20);
      reasons.push(`Filter service overdue (${lastReading.filterHours}/${FILTER_SERVICE_INTERVAL} h)`);
    }

    // 4. Hard PJLink Flag Rules
    const flags = lastReading.flags;

    // Error flags -> immediate failure
    if (flags.lamp === 'error' || flags.fan === 'error' || flags.temperature === 'error') {
      healthScore = 0;
      if (flags.temperature === 'error') failureMode = 'filter_overheat';
      else if (flags.fan === 'error') failureMode = 'fan_fault';
      else failureMode = 'lamp_end_of_life';

      reasons.unshift(`Critical alarm: ${Object.entries(flags).filter(([, v]) => v === 'error').map(([k]) => k.toUpperCase()).join(', ')} in ERROR state`);
    }
    // Warning flags -> lower health & accelerate predicted date
    else if (flags.temperature === 'warning') {
      healthScore = Math.min(healthScore, 25);
      failureMode = 'filter_overheat';
      confidence = 'medium'; // driven by assumed flag behaviour
      reasons.unshift('Thermal warning: Elevated internal optical engine temperature detected');
    } else if (flags.fan === 'warning') {
      healthScore = Math.min(healthScore, 30);
      failureMode = 'fan_fault';
      confidence = 'medium';
      reasons.unshift('Cooling fan warning: RPM below nominal target threshold');
    } else if (flags.filter === 'warning') {
      healthScore = Math.min(healthScore, 50);
      reasons.push('Air intake airflow restricted; filter inspection needed');
    }

    // Determine discrete state
    let healthState: HealthState = 'healthy';
    if (healthScore <= 0) {
      healthState = 'failed';
    } else if (healthScore <= 35) {
      healthState = 'imminent';
    } else if (healthScore <= 70) {
      healthState = 'degrading';
    } else {
      healthState = 'healthy';
    }

    // Calculate predicted failure date
    let predictedFailureAt: string | null = null;
    let finalDays: number | null = null;

    if (healthState === 'failed') {
      predictedFailureAt = 'Failed';
      finalDays = 0;
    } else if (healthState === 'imminent') {
      // If thermal or fan, fails in 2-4 days; if lamp, estDaysRemaining
      if (failureMode === 'filter_overheat' || failureMode === 'fan_fault') {
        finalDays = 3;
      } else {
        finalDays = Math.min(estDaysRemaining, 14);
      }
      const d = new Date(Date.now() + finalDays * 86400000);
      predictedFailureAt = d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    } else if (healthState === 'degrading') {
      finalDays = Math.min(estDaysRemaining, 45);
      const d = new Date(Date.now() + finalDays * 86400000);
      predictedFailureAt = d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    } else {
      finalDays = estDaysRemaining;
      const d = new Date(Date.now() + finalDays * 86400000);
      predictedFailureAt = d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
    }

    return {
      deviceId,
      roomId: lastReading.roomId,
      healthScore: Math.round(healthScore),
      healthState,
      predictedFailureAt,
      daysRemaining: finalDays,
      confidence,
      failureMode,
      reasons,
      lastReading
    };
  }
}

// Single instance for ALL projectors
export const projectorPredictor = new ProjectorPredictor();
