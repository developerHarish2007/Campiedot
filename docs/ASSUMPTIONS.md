# Projector Predictive Maintenance — Engineering Assumptions

All values below are explicit demo assumptions for the 5 PG smart-lab projectors (`PG-102-PROJ`, `PG-201-PROJ`, `PG-202-PROJ`, `PG-302-PROJ`, `PG-402-PROJ`).

## 1. Physical Ratings & Normal Operation
- **Rated Lamp Life:** `3000 hours` (Assumed standard for educational DLP/3LCD overhead projectors).
- **Filter Cleaning Interval:** `500 hours` (Assumed manufacturer recommended service schedule).
- **Daily Operating Usage:** `~6.0 hours/day` (Derived from 3 two-hour lecture slots daily, with ±0.5 h random fluctuation).
- **Staggered Baseline Hours:**
  - `PG-201-PROJ`: **2,740 h** (near end of life, ~91% wear)
  - `PG-102-PROJ`: **1,480 h** (mid-life, ~49% wear)
  - `PG-402-PROJ`: **1,050 h** (early-mid life, ~35% wear)
  - `PG-202-PROJ`: **720 h** (low wear, ~24% wear)
  - `PG-302-PROJ`: **390 h** (near-new, ~13% wear)

## 2. Injected Fault Behaviors (Assumed Progression)
- **Lamp Wearing Out:** Instant jump to `~92% of rated life` (2,760 h); triggers `lamp=warning`, escalation to `lamp=error` when reaching 3,000 h.
- **Dirty Filter:** Filter hours exceed 500 h; triggers `filter=warning`. Thermal accumulation triggers `temperature=warning` after 2 simulated days and thermal shutdown `temperature=error` after 5 simulated days.
- **Fan Fault:** Fan RPM degradation triggers `fan=warning` immediately; mechanical seizure triggers `fan=error` and `temperature=error` after 3 simulated days.

## 3. Model Methodology
- **Classification:** Rules + Trend analysis (PJLink status flags + 7-day moving average hourly run-rate).
- **Confidence Rating:** Lowered to `medium` or `low` when telemetry packets are dropped or when warnings reflect assumed fault rules rather than steady-state trend.
