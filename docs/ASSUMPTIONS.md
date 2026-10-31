# Projector Predictive Maintenance — Engineering Assumptions

All values below are explicit demo assumptions for the 5 PG smart-lab projectors across Floors 0 to 4 (`PG-001-PROJ`, `PG-102-PROJ`, `PG-201-PROJ`, `PG-302-PROJ`, `PG-402-PROJ`).

## 1. Physical Ratings & Schedule
- **Rated Lamp Life:** `3000 hours` (ASSUMED standard for educational 3LCD/DLP overhead projectors).
- **Filter Service Interval:** `500 hours` (ASSUMED manufacturer preventive cleaning interval).
- **Daily Operating Usage:** `6.0 hours/day` (ASSUMED deterministic scheduled operation: three 2-hour lecture sessions daily).
- **Baseline Date:** `2026-10-31` (scripted start of pilot simulation).

## 2. Scripted Pilot Demo Scenario (Floors 0 to 4)
- **Floor 0 (`PG-001-PROJ`):** Healthy. Base lamp 600 h, filter 100 h. Stays **HEALTHY** (green) across all 30 days.
- **Floor 1 (`PG-102-PROJ`):** Healthy mid-life. Base lamp 1500 h, filter 150 h. Stays **HEALTHY** (green) across all 30 days.
- **Floor 2 (`PG-201-PROJ`):** Lamp End-of-Life. Base lamp 2790 h. Reaches 3000 h limit at **Day 35**.
  - Days 0–4: **HEALTHY** (> 30 days remaining).
  - Days 5–21: **DEGRADING** (14 to 30 days remaining).
  - Day 14: Preventive Work Order `WO-2026-PG201-01` triggered (predicted failure ≤ 21 days). Parts stock = 0 (`BLOCKED`).
  - Days 22–30: **IMMINENT FAILURE** (< 14 days remaining).
- **Floor 3 (`PG-302-PROJ`):** Fan Fault. Base lamp 800 h. Healthy until Day 11.
  - Day 12: `fan=warning` triggered (bearing degradation). Work order triggered immediately.
  - Day 22: `fan=error` triggered (ASSUMED 10-day escalation from warning to full bearing lockup) → **FAILED**.
- **Floor 4 (`PG-402-PROJ`):** Dirty Filter. Base filter 350 h, base lamp 1100 h.
  - Day 25: Filter hours reach 500 h interval → `temperature=warning` (airflow obstruction).
  - Day 35: `temperature=error` triggered (ASSUMED 10-day escalation from warning to thermal trip) → **FAILED**.

## 3. Determinism, Explainability & Work Orders
- **Determinism:** NO random noise and NO dropouts by default. Sensor noise & dropouts toggle available for data-quality testing.
- **Rolling Rate:** Computed from device's own 14-day rolling mean (with linear interpolation for missing packets). Failure date moves ≤ 1 day per day for healthy devices.
- **Health Monotonicity:** Health score (0–100) is strictly non-increasing over time unless reset or fixed.
- **Earliest Reason Rule:** The predicted failure date equals the earliest of all contributing reasons. "Driven by: <reason>" is always listed first with exact remaining days and calendar date.
- **Confidence Rating:** `High` by default; lowers to `Medium` only when packet dropouts are active or when failure date relies on an ASSUMED 10-day flag escalation rule.
- **Closed-Loop Work Order Policy:** Predictor generates maintenance work orders but cannot approve its own order; technician confirmation required.
