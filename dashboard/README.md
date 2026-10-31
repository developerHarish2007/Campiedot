# CampusOps: Intelligent Campus Operations & Consequence Platform
**Target Campus:** SRM Easwari Engineering College (Autonomous), Ramapuram, Chennai  
**Geographic Coordinates:** `13.0324° N, 80.1810° E`

---

## 1. Vision & Core Philosophy
CampusOps operates on a strict neuro-symbolic divide and transactional operational loop:
$$\text{Simulate (Read-Only)} \longrightarrow \text{Approve (Separation of Duties)} \longrightarrow \text{Execute (Revalidated Atomic Tx)} \longrightarrow \text{Prove (Live DB Invariants)}$$

* **Neuro-Symbolic Isolation:** AI is bounded to unstructured text extraction, stateful conversational slot clarification, duplicate semantic hints, and grounded natural-language briefing phrasing. AI never makes decisions regarding RBAC permissions, scheduling, room allocations, inventory reservations, approvals, or state transitions.
* **Zero External I/O in DB Transactions:** LLM API queries, SMTP/webhook notifications, and external HTTP calls execute strictly outside operational database transaction boundaries.

---

## 2. SRM Easwari Campus Architecture & 2.5D GeoJSON Twin
The spatial digital twin maps the 5 core campus blocks:
1. `EEC-MAIN`: Main Administrative Block (4 floors, 14.0m height)
2. `EEC-ACAD`: Academic Tech Block [CSE, IT, AI&DS, ECE] (5 floors, 17.5m height)
3. `EEC-MECH-PG`: Mechanical, Civil & Central PG Library Block (4 floors, 14.0m height)
4. `EEC-ROBOTICS`: ABB Robotics Research & Automation Centre (2 floors, 7.0m height)
5. `EEC-AUD-FC`: TRP Auditorium & Central Food Court (2 floors, 8.0m height)

### Demonstration Fixtures
* **Exam Disruption Venue:** Room `RM-ACAD-204` (CSE/IT 2nd Floor Smart Classroom, capacity 110, semester exam scheduled).
* **Alternative Relocation Room:** Room `RM-MECH-102` (PG Mechanical Block, capacity 125, projector & wheelchair ramp verified).
* **Faulty Part Shortage:** `PART-MCCB-63A` (63A 4-Pole Distribution Breaker) seeded with `physical_on_hand_qty = 0, available_qty = 0, reserved_qty = 0`.
* **Wi-Fi Storm Nodes:** Labs `LAB-ACAD-301`, `LAB-ACAD-302`, and `LAB-ACAD-304` sharing upstream PoE distribution switch `SW-CORE-ACAD-F3`.

---

## 3. Database Invariant Kernel (PostgreSQL 16)
The symbolic kernel enforces 6 critical invariants directly within PostgreSQL:
1. **Room Double-Booking Prevention:** GiST exclusion constraint (`btree_gist`) over `TSTZRANGE` preventing overlapping active bookings (`CONFIRMED`, `CONTINGENCY_HOLD`, `MAINTENANCE_BLOCK`).
2. **3-Bucket Inventory Conservation:** Table check constraint `CHECK (physical_on_hand_qty = available_qty + reserved_qty)` backed by an append-only `inventory_movements` tamper guard trigger.
3. **DAG Cycle Prevention:** Recursive reachability check with transaction-scoped advisory locking (`pg_advisory_xact_lock`) raising `SQLSTATE 23514` on circular dependency insertion.
4. **Finite State Machine Enforcement:** Reference matrix `fsm_state_transitions` mapping valid transitions and actor roles, enforced via `trg_work_order_fsm_enforcement`.
5. **Approval Scope Invalidation:** Cryptographic SHA-256 snapshot hashing (`node:category:cost:dept:parts`); any post-approval mutation automatically invalidates the approval record.
6. **Immutable Audit Ledger:** `audit_logs` trigger unconditionally blocking `UPDATE`, `DELETE`, and `TRUNCATE`.

---

## 4. Setup & Running the Platform

### Windows 1-Click Launch
Double-click or run:
```cmd
run.bat
```
This automatically sets up `.env`, locates Python, checks dependencies, launches the **FastAPI backend** on `http://localhost:8000`, the **Vite React frontend** on `http://localhost:5173`, and opens the browser.

*(To initialize or re-seed the PostgreSQL database schema and test fixtures, run `setup_database.bat`)*

---

### Manual Setup

#### Prerequisites
* Python 3.12+
* PostgreSQL 16+ (or Docker with `pgvector/pgvector:pg16`)
* Node.js 18+

#### Environment Configuration
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```

#### Starting the Database with Docker
```bash
docker compose up -d postgres
```

#### Seeding Campus Data
```bash
python scripts/setup_db.py
python scripts/seed_demo.py
```

#### Running Phase 1 Invariant Verification
```bash
python scripts/verify_phase1.py
```
