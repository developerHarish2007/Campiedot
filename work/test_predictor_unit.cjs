// Unit test for Projector Simulator and Deterministic Predictor
const { ProjectorSimulator, PG_PROJECTOR_IDS, BASE_SIM_DATE } = require('../src/sim/projectorSim.ts');
const { ProjectorPredictor } = require('../src/sim/projectorPredictor.ts');
const assert = require('assert');

console.log('Testing Projector Predictor Determinism & Explainability...');
const sim = new ProjectorSimulator();
const pred = new ProjectorPredictor();

// 1. Test Determinism: No-fault device date moves <= 1 day per day, health non-increasing
const healthyDev = 'PG-001-PROJ';
let prevHealth = 100;
let prevFailDate = null;

for (let day = 0; day <= 30; day++) {
  const readings = sim.getReadingsUpToDay(healthyDev, day);
  const result = pred.predict(healthyDev, readings);

  // Health is non-increasing
  assert(result.healthScore <= prevHealth, `Health increased on day ${day}: ${result.healthScore} > ${prevHealth}`);
  prevHealth = result.healthScore;

  // Failure date moves at most 1 day between consecutive days
  if (prevFailDate) {
    const d1 = new Date(prevFailDate);
    const d2 = new Date(result.predictedFailureAt);
    const diffDays = Math.abs((d2 - d1) / 86400000);
    assert(diffDays <= 1.0, `Failure date shifted by ${diffDays} days (>1) on day ${day}`);
  }
  prevFailDate = result.predictedFailureAt;

  // Driving reason is listed first and matches failure date
  assert(result.reasons[0].startsWith('Driven by:'), 'Driving reason must be first');
  assert(result.reasons[0].includes(result.predictedFailureAt), 'Driving reason date must match predictedFailureAt');
  assert.strictEqual(result.confidence, 'High', 'Confidence must be High by default');
}
console.log('✔ Determinism test passed: Date moves <= 1 day/day and health is monotonically non-increasing');

// 2. Test Pilot Scenario Milestones
// Floor 2 (PG-201): Day 0 green, Day 5 degrading (<=30 days), Day 14 work order blocked, Day 22 imminent (<14 days)
const pg201_d0 = pred.predict('PG-201-PROJ', sim.getReadingsUpToDay('PG-201-PROJ', 0));
assert.strictEqual(pg201_d0.healthState, 'healthy', 'Floor 2 day 0 must be healthy');
assert.strictEqual(pg201_d0.daysRemaining, 35, 'Floor 2 day 0 must have 35 days remaining');

const pg201_d5 = pred.predict('PG-201-PROJ', sim.getReadingsUpToDay('PG-201-PROJ', 5));
assert.strictEqual(pg201_d5.healthState, 'degrading', 'Floor 2 day 5 must be degrading (30 days left)');
assert.strictEqual(pg201_d5.daysRemaining, 30, 'Floor 2 day 5 must have 30 days remaining');

const pg201_d14 = pred.predict('PG-201-PROJ', sim.getReadingsUpToDay('PG-201-PROJ', 14));
assert.strictEqual(pg201_d14.daysRemaining, 21, 'Floor 2 day 14 must have 21 days remaining');
assert(pg201_d14.workOrder !== null, 'Floor 2 day 14 must trigger work order');
assert.strictEqual(pg201_d14.workOrder.stockCount, 0, 'Floor 2 work order stock must be 0');
assert.strictEqual(pg201_d14.workOrder.isBlocked, true, 'Floor 2 work order must be BLOCKED');

const pg201_d22 = pred.predict('PG-201-PROJ', sim.getReadingsUpToDay('PG-201-PROJ', 22));
assert.strictEqual(pg201_d22.healthState, 'imminent', 'Floor 2 day 22 must be imminent (<14 days)');
assert.strictEqual(pg201_d22.daysRemaining, 13, 'Floor 2 day 22 must have 13 days remaining');

// Floor 3 (PG-302): Fan fault. Healthy until day 11. Day 12 warning + work order. Day 22 error (failed).
const pg302_d11 = pred.predict('PG-302-PROJ', sim.getReadingsUpToDay('PG-302-PROJ', 11));
assert.strictEqual(pg302_d11.healthState, 'healthy', 'Floor 3 day 11 must be healthy');

const pg302_d12 = pred.predict('PG-302-PROJ', sim.getReadingsUpToDay('PG-302-PROJ', 12));
assert.strictEqual(pg302_d12.healthState, 'imminent', 'Floor 3 day 12 must be imminent');
assert(pg302_d12.workOrder !== null, 'Floor 3 day 12 must have work order');
assert.strictEqual(pg302_d12.workOrder.stockCount, 2, 'Floor 3 work order stock must be 2');

const pg302_d22 = pred.predict('PG-302-PROJ', sim.getReadingsUpToDay('PG-302-PROJ', 22));
assert.strictEqual(pg302_d22.healthState, 'failed', 'Floor 3 day 22 must be failed');

console.log('✔ Pilot scenario milestones passed for all floors');

