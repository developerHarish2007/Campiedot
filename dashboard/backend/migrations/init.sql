-- ==============================================================================
-- CAMPUSOPS: AUTONOMOUS OPERATIONS & CONSEQUENCE PLATFORM (POSTGRESQL 16 DDL)
-- TARGET CAMPUS: SRM EASWARI ENGINEERING COLLEGE (AUTONOMOUS), RAMAPURAM, CHENNAI
-- ==============================================================================
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "btree_gist";
-- CREATE EXTENSION IF NOT EXISTS vector;
-- ------------------------------------------------------------------------------
-- 1. ENUMS
-- ------------------------------------------------------------------------------
CREATE TYPE user_role AS ENUM (
    'STUDENT_FACULTY',
    'TECHNICIAN',
    'DEPT_MANAGER',
    'FACILITIES_ADMIN',
    'PROCUREMENT_APPROVER',
    'SYS_ADMIN'
);
CREATE TYPE issue_category AS ENUM (
    'ELECTRICAL',
    'PLUMBING',
    'NETWORK',
    'STRUCTURAL_SAFETY',
    'SOS',
    'SWEEPER',
    'HVAC',
    'AV_EQUIPMENT',
    'GENERAL'
);
CREATE TYPE priority_level AS ENUM (
    'P3_LOW',
    'P2_MEDIUM',
    'P1_HIGH',
    'P0_CRITICAL'
);
CREATE TYPE wo_state AS ENUM (
    'INGESTED',
    'AWAITING_CLARIFICATION',
    'TRIAGED',
    'MERGED_DUPLICATE',
    'ASSIGNED',
    'IN_PROGRESS',
    'BLOCKED_PARTS',
    'PENDING_APPROVAL',
    'APPROVED_READY',
    'RESOLVED',
    'CLOSED',
    'ESCALATED_SAFETY_REVIEW'
);
-- ------------------------------------------------------------------------------
-- 2. SECURE TRANSACTION-CONTEXT TABLE & FUNCTIONS
-- ------------------------------------------------------------------------------
CREATE TABLE security_context_session (
    backend_pid INT PRIMARY KEY DEFAULT pg_backend_pid(),
    actor_id UUID NOT NULL,
    actor_role user_role NOT NULL,
    department_id UUID,
    established_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE OR REPLACE FUNCTION set_secure_context(p_actor_id UUID, p_role user_role, p_dept_id UUID DEFAULT NULL)
RETURNS VOID AS $$
BEGIN
    INSERT INTO security_context_session (backend_pid, actor_id, actor_role, department_id, established_at)
    VALUES (pg_backend_pid(), p_actor_id, p_role, p_dept_id, NOW())
    ON CONFLICT (backend_pid) 
    DO UPDATE SET actor_id = EXCLUDED.actor_id,
                  actor_role = EXCLUDED.actor_role,
                  department_id = EXCLUDED.department_id,
                  established_at = NOW();
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
CREATE OR REPLACE FUNCTION get_current_actor_role() RETURNS user_role AS $$
DECLARE
    v_role user_role;
BEGIN
    SELECT actor_role INTO v_role FROM security_context_session WHERE backend_pid = pg_backend_pid();
    IF v_role IS NULL THEN
        RAISE EXCEPTION 'Security Violation: No secure transaction context established for pid %', pg_backend_pid();
    END IF;
    RETURN v_role;
END;
$$ LANGUAGE plpgsql STABLE;
CREATE OR REPLACE FUNCTION get_current_actor_id() RETURNS UUID AS $$
DECLARE
    v_id UUID;
BEGIN
    SELECT actor_id INTO v_id FROM security_context_session WHERE backend_pid = pg_backend_pid();
    IF v_id IS NULL THEN
        RAISE EXCEPTION 'Security Violation: No secure actor context established for pid %', pg_backend_pid();
    END IF;
    RETURN v_id;
END;
$$ LANGUAGE plpgsql STABLE;
-- ------------------------------------------------------------------------------
-- 3. DEPARTMENTS & USERS
-- ------------------------------------------------------------------------------
CREATE TABLE departments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code VARCHAR(32) UNIQUE NOT NULL,
    name VARCHAR(120) NOT NULL,
    total_budget NUMERIC(12, 2) NOT NULL CHECK (total_budget >= 0),
    available_budget NUMERIC(12, 2) NOT NULL CHECK (available_budget >= 0),
    encumbered_budget NUMERIC(12, 2) NOT NULL DEFAULT 0.00 CHECK (encumbered_budget >= 0),
    spent_budget NUMERIC(12, 2) NOT NULL DEFAULT 0.00 CHECK (spent_budget >= 0),
    manager_approval_limit NUMERIC(12, 2) NOT NULL DEFAULT 15000.00,
    CONSTRAINT dept_budget_invariant CHECK (total_budget = available_budget + encumbered_budget + spent_budget)
);
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    full_name VARCHAR(120) NOT NULL,
    role user_role NOT NULL,
    department_id UUID REFERENCES departments(id),
    is_available BOOLEAN NOT NULL DEFAULT TRUE,
    active_workload_count INT NOT NULL DEFAULT 0 CHECK (active_workload_count >= 0),
    max_concurrent_workload INT NOT NULL DEFAULT 4,
    base_building_code VARCHAR(32)
);
CREATE TABLE staff_shifts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    shift_window TSTZRANGE NOT NULL,
    CONSTRAINT valid_shift_range CHECK (NOT isempty(shift_window) AND NOT lower_inf(shift_window) AND NOT upper_inf(shift_window))
);
CREATE TABLE staff_skills (
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    skill issue_category NOT NULL,
    proficiency_level INT NOT NULL CHECK (proficiency_level BETWEEN 1 AND 5),
    PRIMARY KEY (user_id, skill)
);
-- ------------------------------------------------------------------------------
-- 4. CAMPUS TOPOLOGY (DAG) & CYCLE DETECTION
-- ------------------------------------------------------------------------------
CREATE TABLE campus_nodes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    node_code VARCHAR(64) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    node_type VARCHAR(32) NOT NULL CHECK (node_type IN ('BUILDING', 'ELECTRICAL_PANEL', 'NETWORK_SWITCH', 'HVAC_AHU', 'ROOM', 'EQUIPMENT')),
    building_code VARCHAR(32) NOT NULL,
    floor_number INT NOT NULL DEFAULT 1,
    room_capacity INT DEFAULT 0,
    room_type VARCHAR(32) DEFAULT 'CLASSROOM',
    room_features TEXT[] DEFAULT '{}',
    is_operational BOOLEAN NOT NULL DEFAULT TRUE,
    criticality_weight INT NOT NULL DEFAULT 10 CHECK (criticality_weight BETWEEN 1 AND 30)
);
CREATE TABLE node_dependencies (
    parent_node_id UUID NOT NULL REFERENCES campus_nodes(id) ON DELETE CASCADE,
    child_node_id UUID NOT NULL REFERENCES campus_nodes(id) ON DELETE CASCADE,
    dependency_domain issue_category NOT NULL,
    PRIMARY KEY (parent_node_id, child_node_id, dependency_domain),
    CONSTRAINT no_self_dependency CHECK (parent_node_id <> child_node_id)
);
CREATE OR REPLACE FUNCTION trg_fn_prevent_dag_cycles()
RETURNS TRIGGER AS $$
DECLARE
    v_is_reachable BOOLEAN;
BEGIN
    PERFORM pg_advisory_xact_lock(hashtext(NEW.dependency_domain::text));
    WITH RECURSIVE reachability AS (
        SELECT child_node_id AS current_id, 1 AS depth
        FROM node_dependencies
        WHERE parent_node_id = NEW.child_node_id AND dependency_domain = NEW.dependency_domain
        UNION
        SELECT nd.child_node_id, r.depth + 1
        FROM node_dependencies nd
        JOIN reachability r ON nd.parent_node_id = r.current_id
        WHERE nd.dependency_domain = NEW.dependency_domain AND r.depth < 12
    )
    SELECT EXISTS (SELECT 1 FROM reachability WHERE current_id = NEW.parent_node_id) INTO v_is_reachable;
    IF v_is_reachable THEN
        RAISE EXCEPTION 'DAG Cycle Violation: Adding edge % -> % creates a loop in domain %', 
            NEW.parent_node_id, NEW.child_node_id, NEW.dependency_domain
            USING ERRCODE = '23514';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
CREATE TRIGGER trg_enforce_dag_acyclic
BEFORE INSERT OR UPDATE ON node_dependencies
FOR EACH ROW EXECUTE FUNCTION trg_fn_prevent_dag_cycles();
-- ------------------------------------------------------------------------------
-- 5. IDEMPOTENCY LEDGER WITH WORKER LEASES
-- ------------------------------------------------------------------------------
CREATE TABLE processed_events (
    source VARCHAR(64) NOT NULL,
    idempotency_key VARCHAR(128) NOT NULL,
    payload_hash VARCHAR(64) NOT NULL,
    status VARCHAR(32) NOT NULL CHECK (status IN ('PROCESSING', 'COMPLETED', 'FAILED_RETRYABLE')),
    worker_id VARCHAR(64) NOT NULL,
    attempt_count INT NOT NULL DEFAULT 1,
    claimed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    lease_expires_at TIMESTAMPTZ NOT NULL DEFAULT (NOW() + INTERVAL '30 seconds'),
    response_status INT,
    response_payload JSONB,
    PRIMARY KEY (source, idempotency_key)
);
-- ------------------------------------------------------------------------------
-- 6. AUTHORITATIVE INVENTORY & 3-BUCKET INVARIANT
-- ------------------------------------------------------------------------------
CREATE TABLE inventory_parts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    sku VARCHAR(64) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    category issue_category NOT NULL,
    physical_on_hand_qty INT NOT NULL DEFAULT 0 CHECK (physical_on_hand_qty >= 0),
    available_qty INT NOT NULL DEFAULT 0 CHECK (available_qty >= 0),
    reserved_qty INT NOT NULL DEFAULT 0 CHECK (reserved_qty >= 0),
    reorder_threshold INT NOT NULL DEFAULT 2,
    unit_cost NUMERIC(10, 2) NOT NULL CHECK (unit_cost >= 0),
    lead_time_hours INT NOT NULL DEFAULT 24,
    CONSTRAINT inventory_three_bucket_invariant CHECK (physical_on_hand_qty = available_qty + reserved_qty)
);
CREATE TABLE inventory_movements (
    id BIGSERIAL PRIMARY KEY,
    part_id UUID NOT NULL REFERENCES inventory_parts(id),
    work_order_id UUID,
    actor_id UUID NOT NULL,
    movement_type VARCHAR(32) NOT NULL CHECK (movement_type IN ('RECEIPT', 'RESERVE', 'RELEASE', 'CONSUME', 'AUDIT_ADJUSTMENT')),
    delta_physical INT NOT NULL,
    delta_available INT NOT NULL,
    delta_reserved INT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE OR REPLACE FUNCTION trg_fn_enforce_inventory_ledger()
RETURNS TRIGGER AS $$
BEGIN
    IF (NEW.physical_on_hand_qty <> OLD.physical_on_hand_qty) 
       OR (NEW.available_qty <> OLD.available_qty) 
       OR (NEW.reserved_qty <> OLD.reserved_qty) THEN
        IF NOT EXISTS (
            SELECT 1 FROM inventory_movements 
            WHERE part_id = NEW.id 
              AND delta_physical = (NEW.physical_on_hand_qty - OLD.physical_on_hand_qty)
              AND delta_available = (NEW.available_qty - OLD.available_qty)
              AND delta_reserved = (NEW.reserved_qty - OLD.reserved_qty)
              AND created_at >= NOW() - INTERVAL '5 seconds'
        ) THEN
            RAISE EXCEPTION 'Inventory Security Violation: Direct modification of balances without movement ledger entry is forbidden.';
        END IF;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
CREATE TRIGGER trg_inventory_tamper_guard
BEFORE UPDATE ON inventory_parts
FOR EACH ROW EXECUTE FUNCTION trg_fn_enforce_inventory_ledger();
-- ------------------------------------------------------------------------------
-- 7. WORK ORDERS, FSM & RESERVATIONS
-- ------------------------------------------------------------------------------
CREATE TABLE work_orders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ticket_number SERIAL UNIQUE,
    conversation_thread_id VARCHAR(128) NOT NULL,
    reporter_user_id UUID NOT NULL REFERENCES users(id),
    target_node_id UUID REFERENCES campus_nodes(id),
    parent_master_wo_id UUID REFERENCES work_orders(id),
    category issue_category,
    reporter_urgency priority_level NOT NULL DEFAULT 'P2_MEDIUM',
    calculated_priority priority_level NOT NULL DEFAULT 'P2_MEDIUM',
    impact_score INT NOT NULL DEFAULT 20 CHECK (impact_score BETWEEN 0 AND 100),
    state wo_state NOT NULL DEFAULT 'INGESTED',
    raw_description TEXT NOT NULL,
    ai_summary TEXT,
    partial_slots JSONB NOT NULL DEFAULT '{}'::jsonb,
    clarification_question TEXT,
    assigned_tech_id UUID REFERENCES users(id),
    department_id UUID REFERENCES departments(id),
    estimated_cost NUMERIC(12, 2) NOT NULL DEFAULT 0.00 CHECK (estimated_cost >= 0),
    estimated_duration_mins INT NOT NULL DEFAULT 60,
    required_parts_hash VARCHAR(64) NOT NULL DEFAULT 'EMPTY',
    reassignment_count INT NOT NULL DEFAULT 0,
    correlator_reporter_count INT NOT NULL DEFAULT 1,
    sla_target_seconds INT NOT NULL DEFAULT 14400,
    sla_accumulated_active_seconds INT NOT NULL DEFAULT 0,
    sla_last_resumed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    sla_is_paused BOOLEAN NOT NULL DEFAULT FALSE,
    sla_breached BOOLEAN NOT NULL DEFAULT FALSE,
    blocked_reason TEXT,
    embedding real[],
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    resolved_at TIMESTAMPTZ
);
CREATE TABLE part_reservations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    work_order_id UUID NOT NULL REFERENCES work_orders(id) ON DELETE CASCADE,
    part_id UUID NOT NULL REFERENCES inventory_parts(id),
    requested_qty INT NOT NULL CHECK (requested_qty > 0),
    locked_unit_cost NUMERIC(10, 2) NOT NULL CHECK (locked_unit_cost >= 0),
    status VARCHAR(24) NOT NULL CHECK (status IN ('RESERVED', 'SHORTAGE_BLOCKED', 'CONSUMED', 'RELEASED')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (work_order_id, part_id)
);
CREATE TABLE fsm_state_transitions (
    from_state wo_state NOT NULL,
    to_state wo_state NOT NULL,
    allowed_roles user_role[] NOT NULL,
    PRIMARY KEY (from_state, to_state)
);
INSERT INTO fsm_state_transitions (from_state, to_state, allowed_roles) VALUES
('INGESTED', 'AWAITING_CLARIFICATION', ARRAY['SYS_ADMIN'::user_role, 'FACILITIES_ADMIN'::user_role]),
('INGESTED', 'TRIAGED', ARRAY['SYS_ADMIN'::user_role, 'FACILITIES_ADMIN'::user_role, 'STUDENT_FACULTY'::user_role]),
('INGESTED', 'ASSIGNED', ARRAY['SYS_ADMIN'::user_role, 'FACILITIES_ADMIN'::user_role, 'DEPT_MANAGER'::user_role]),
('INGESTED', 'MERGED_DUPLICATE', ARRAY['SYS_ADMIN'::user_role, 'FACILITIES_ADMIN'::user_role, 'STUDENT_FACULTY'::user_role]),
('INGESTED', 'CLOSED', ARRAY['SYS_ADMIN'::user_role, 'FACILITIES_ADMIN'::user_role]),
('TRIAGED', 'MERGED_DUPLICATE', ARRAY['SYS_ADMIN'::user_role, 'FACILITIES_ADMIN'::user_role, 'STUDENT_FACULTY'::user_role]),
('AWAITING_CLARIFICATION', 'TRIAGED', ARRAY['SYS_ADMIN'::user_role, 'FACILITIES_ADMIN'::user_role, 'STUDENT_FACULTY'::user_role]),
('AWAITING_CLARIFICATION', 'ASSIGNED', ARRAY['SYS_ADMIN'::user_role, 'FACILITIES_ADMIN'::user_role, 'DEPT_MANAGER'::user_role]),
('TRIAGED', 'ASSIGNED', ARRAY['SYS_ADMIN'::user_role, 'FACILITIES_ADMIN'::user_role, 'DEPT_MANAGER'::user_role]),
('TRIAGED', 'BLOCKED_PARTS', ARRAY['TECHNICIAN'::user_role, 'SYS_ADMIN'::user_role, 'FACILITIES_ADMIN'::user_role]),
('ASSIGNED', 'TRIAGED', ARRAY['SYS_ADMIN'::user_role, 'FACILITIES_ADMIN'::user_role, 'DEPT_MANAGER'::user_role]),
('ASSIGNED', 'IN_PROGRESS', ARRAY['TECHNICIAN'::user_role, 'SYS_ADMIN'::user_role]),
('ASSIGNED', 'RESOLVED', ARRAY['TECHNICIAN'::user_role, 'SYS_ADMIN'::user_role]),
('ASSIGNED', 'BLOCKED_PARTS', ARRAY['TECHNICIAN'::user_role, 'SYS_ADMIN'::user_role, 'FACILITIES_ADMIN'::user_role]),
('IN_PROGRESS', 'BLOCKED_PARTS', ARRAY['TECHNICIAN'::user_role, 'SYS_ADMIN'::user_role]),
('IN_PROGRESS', 'PENDING_APPROVAL', ARRAY['TECHNICIAN'::user_role, 'DEPT_MANAGER'::user_role]),
('BLOCKED_PARTS', 'IN_PROGRESS', ARRAY['TECHNICIAN'::user_role, 'SYS_ADMIN'::user_role, 'FACILITIES_ADMIN'::user_role]),
('BLOCKED_PARTS', 'RESOLVED', ARRAY['TECHNICIAN'::user_role, 'SYS_ADMIN'::user_role, 'FACILITIES_ADMIN'::user_role]),
('BLOCKED_PARTS', 'PENDING_APPROVAL', ARRAY['TECHNICIAN'::user_role, 'DEPT_MANAGER'::user_role]),
('BLOCKED_PARTS', 'ASSIGNED', ARRAY['SYS_ADMIN'::user_role, 'FACILITIES_ADMIN'::user_role]),
('PENDING_APPROVAL', 'APPROVED_READY', ARRAY['DEPT_MANAGER'::user_role, 'PROCUREMENT_APPROVER'::user_role, 'FACILITIES_ADMIN'::user_role]),
('APPROVED_READY', 'ASSIGNED', ARRAY['SYS_ADMIN'::user_role, 'FACILITIES_ADMIN'::user_role]),
('APPROVED_READY', 'IN_PROGRESS', ARRAY['TECHNICIAN'::user_role, 'SYS_ADMIN'::user_role]),
('IN_PROGRESS', 'RESOLVED', ARRAY['TECHNICIAN'::user_role, 'SYS_ADMIN'::user_role]),
('RESOLVED', 'CLOSED', ARRAY['FACILITIES_ADMIN'::user_role, 'SYS_ADMIN'::user_role]),
('TRIAGED', 'CLOSED', ARRAY['SYS_ADMIN'::user_role, 'FACILITIES_ADMIN'::user_role]),
('ASSIGNED', 'CLOSED', ARRAY['SYS_ADMIN'::user_role, 'FACILITIES_ADMIN'::user_role]),
('IN_PROGRESS', 'CLOSED', ARRAY['SYS_ADMIN'::user_role, 'FACILITIES_ADMIN'::user_role]),
('AWAITING_CLARIFICATION', 'CLOSED', ARRAY['SYS_ADMIN'::user_role, 'FACILITIES_ADMIN'::user_role]),
('MERGED_DUPLICATE', 'CLOSED', ARRAY['SYS_ADMIN'::user_role, 'FACILITIES_ADMIN'::user_role]),
('BLOCKED_PARTS', 'CLOSED', ARRAY['SYS_ADMIN'::user_role, 'FACILITIES_ADMIN'::user_role]),
('IN_PROGRESS', 'ESCALATED_SAFETY_REVIEW', ARRAY['TECHNICIAN'::user_role, 'FACILITIES_ADMIN'::user_role]);
CREATE OR REPLACE FUNCTION trg_fn_enforce_wo_fsm()
RETURNS TRIGGER AS $$
DECLARE
    v_role user_role;
    v_allowed BOOLEAN;
BEGIN
    IF OLD.state = NEW.state THEN
        RETURN NEW;
    END IF;
    v_role := get_current_actor_role();
    SELECT EXISTS (
        SELECT 1 FROM fsm_state_transitions
        WHERE from_state = OLD.state 
          AND to_state = NEW.state 
          AND v_role = ANY(allowed_roles)
    ) INTO v_allowed;
    IF NOT v_allowed THEN
        RAISE EXCEPTION 'FSM Violation: Role % is not permitted to transition work order from % to %',
            v_role, OLD.state, NEW.state;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
CREATE TRIGGER trg_work_order_fsm_enforcement
BEFORE UPDATE OF state ON work_orders
FOR EACH ROW EXECUTE FUNCTION trg_fn_enforce_wo_fsm();
-- ------------------------------------------------------------------------------
-- 8. APPROVALS & SNAPSHOT HASHING
-- ------------------------------------------------------------------------------
CREATE TABLE approvals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    work_order_id UUID NOT NULL REFERENCES work_orders(id) ON DELETE CASCADE,
    approval_type VARCHAR(32) NOT NULL CHECK (approval_type IN ('COSTLY_REPAIR', 'EMERGENCY_PURCHASE', 'SCHEDULE_OVERRIDE')),
    requested_by_user_id UUID NOT NULL REFERENCES users(id),
    approved_by_user_id UUID REFERENCES users(id),
    requested_amount NUMERIC(12, 2) NOT NULL CHECK (requested_amount >= 0),
    snapshot_hash VARCHAR(64) NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'PENDING' CHECK (status IN ('PENDING', 'APPROVED', 'REJECTED', 'INVALIDATED_BY_CHANGE')),
    invalidation_reason TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    decided_at TIMESTAMPTZ,
    CONSTRAINT enforce_no_self_approval CHECK (
        approved_by_user_id IS NULL OR approved_by_user_id <> requested_by_user_id
    )
);
CREATE OR REPLACE FUNCTION fn_compute_canonical_wo_snapshot(p_wo_id UUID)
RETURNS VARCHAR AS $$
DECLARE
    v_canonical_text TEXT;
    v_wo RECORD;
    v_parts_json JSONB;
BEGIN
    SELECT target_node_id, category, estimated_cost, department_id 
    INTO v_wo FROM work_orders WHERE id = p_wo_id;
    SELECT COALESCE(jsonb_agg(
        jsonb_build_object('part_id', part_id, 'qty', requested_qty, 'cost', locked_unit_cost)
        ORDER BY part_id
    ), '[]'::jsonb) INTO v_parts_json
    FROM part_reservations WHERE work_order_id = p_wo_id;
    v_canonical_text := format('node:%s|cat:%s|cost:%s|dept:%s|parts:%s',
        v_wo.target_node_id, v_wo.category, v_wo.estimated_cost, v_wo.department_id, v_parts_json);
    RETURN encode(digest(v_canonical_text, 'sha256'), 'hex');
END;
$$ LANGUAGE plpgsql STABLE;
CREATE OR REPLACE FUNCTION trg_fn_invalidate_approval_on_scope_change()
RETURNS TRIGGER AS $$
DECLARE
    v_wo_id UUID;
    v_current_hash VARCHAR(64);
    v_approval RECORD;
BEGIN
    IF TG_TABLE_NAME = 'work_orders' THEN
        v_wo_id := NEW.id;
    ELSIF TG_TABLE_NAME = 'part_reservations' THEN
        v_wo_id := COALESCE(NEW.work_order_id, OLD.work_order_id);
    END IF;
    v_current_hash := fn_compute_canonical_wo_snapshot(v_wo_id);
    FOR v_approval IN 
        SELECT id, snapshot_hash FROM approvals 
        WHERE work_order_id = v_wo_id AND status IN ('PENDING', 'APPROVED')
    LOOP
        IF v_approval.snapshot_hash <> v_current_hash THEN
            UPDATE approvals 
            SET status = 'INVALIDATED_BY_CHANGE',
                invalidation_reason = 'Scope mutated after approval grant.',
                decided_at = NOW()
            WHERE id = v_approval.id;
            UPDATE work_orders 
            SET state = 'PENDING_APPROVAL' 
            WHERE id = v_wo_id AND state IN ('APPROVED_READY', 'ASSIGNED', 'IN_PROGRESS');
        END IF;
    END LOOP;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;
CREATE TRIGGER trg_wo_approval_invalidation
AFTER UPDATE ON work_orders
FOR EACH ROW EXECUTE FUNCTION trg_fn_invalidate_approval_on_scope_change();
CREATE TRIGGER trg_parts_approval_invalidation
AFTER INSERT OR UPDATE OR DELETE ON part_reservations
FOR EACH ROW EXECUTE FUNCTION trg_fn_invalidate_approval_on_scope_change();
-- ------------------------------------------------------------------------------
-- 9. ROOM BOOKINGS WITH GIST EXCLUSION
-- ------------------------------------------------------------------------------
CREATE TABLE room_bookings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    room_node_id UUID NOT NULL REFERENCES campus_nodes(id),
    booking_type VARCHAR(32) NOT NULL CHECK (booking_type IN ('CLASS', 'EXAM', 'MAINTENANCE_BLOCK', 'CONTINGENCY_HOLD')),
    course_or_event_title VARCHAR(255) NOT NULL,
    faculty_user_id UUID REFERENCES users(id),
    student_count INT NOT NULL DEFAULT 30,
    required_features TEXT[] NOT NULL DEFAULT '{}',
    time_slot TSTZRANGE NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'CONFIRMED' CHECK (status IN ('CONFIRMED', 'CONTINGENCY_HOLD', 'MAINTENANCE_BLOCK', 'IMPACTED_NEEDS_MOVE', 'RELOCATED', 'CANCELLED')),
    linked_work_order_id UUID REFERENCES work_orders(id),
    relocated_to_booking_id UUID REFERENCES room_bookings(id),
    compromise_explanation TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT valid_time_slot_range CHECK (
        NOT isempty(time_slot) AND
        NOT lower_inf(time_slot) AND NOT upper_inf(time_slot) AND
        lower_inc(time_slot) AND NOT upper_inc(time_slot) AND
        upper(time_slot) > lower(time_slot)
    ),
    CONSTRAINT faculty_required_for_classes CHECK (
        (booking_type IN ('CLASS', 'EXAM') AND faculty_user_id IS NOT NULL) OR
        (booking_type IN ('MAINTENANCE_BLOCK', 'CONTINGENCY_HOLD'))
    ),
    CONSTRAINT prevent_room_double_booking
    EXCLUDE USING gist (
        room_node_id WITH =,
        time_slot WITH &&
    ) WHERE (status IN ('CONFIRMED', 'CONTINGENCY_HOLD', 'MAINTENANCE_BLOCK'))
);
CREATE OR REPLACE FUNCTION trg_fn_validate_room_operational()
RETURNS TRIGGER AS $$
DECLARE
    v_is_op BOOLEAN;
BEGIN
    SELECT is_operational INTO v_is_op FROM campus_nodes WHERE id = NEW.room_node_id;
    IF NOT v_is_op AND NEW.booking_type IN ('CLASS', 'EXAM', 'CONTINGENCY_HOLD') THEN
        RAISE EXCEPTION 'Room Booking Violation: Room % is non-operational.', NEW.room_node_id;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
CREATE TRIGGER trg_room_operational_check
BEFORE INSERT OR UPDATE ON room_bookings
FOR EACH ROW EXECUTE FUNCTION trg_fn_validate_room_operational();
-- ------------------------------------------------------------------------------
-- 10. IMMUTABLE AUDIT LOG & TRANSACTIONAL OUTBOX
-- ------------------------------------------------------------------------------
CREATE TABLE audit_logs (
    id BIGSERIAL PRIMARY KEY,
    work_order_id UUID REFERENCES work_orders(id),
    actor_user_id UUID,
    action VARCHAR(64) NOT NULL,
    previous_state VARCHAR(32),
    new_state VARCHAR(32),
    details JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE OR REPLACE FUNCTION trg_fn_audit_immutable()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'Security Violation: audit_logs is append-only.';
END;
$$ LANGUAGE plpgsql;
CREATE TRIGGER trg_audit_tamper_guard_row
BEFORE UPDATE OR DELETE ON audit_logs
FOR EACH ROW EXECUTE FUNCTION trg_fn_audit_immutable();
CREATE TRIGGER trg_audit_tamper_guard_stmt
BEFORE TRUNCATE ON audit_logs
FOR EACH STATEMENT EXECUTE FUNCTION trg_fn_audit_immutable();
CREATE TABLE outbound_notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    recipient_user_id UUID REFERENCES users(id),
    recipient_email VARCHAR(255) NOT NULL,
    channel VARCHAR(32) NOT NULL DEFAULT 'SIMULATED_EMAIL_WEBHOOK',
    subject VARCHAR(255) NOT NULL,
    body TEXT NOT NULL,
    work_order_id UUID REFERENCES work_orders(id),
    delivery_status VARCHAR(24) NOT NULL DEFAULT 'PENDING' CHECK (delivery_status IN ('PENDING', 'DELIVERED', 'FAILED_RETRYABLE', 'DEAD_LETTER')),
    attempt_count INT NOT NULL DEFAULT 0,
    next_retry_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
-- ------------------------------------------------------------------------------
-- 11. LIVE ANALYTICS VIEWS
-- ------------------------------------------------------------------------------
CREATE OR REPLACE VIEW v_analytics_summary AS
SELECT
    COUNT(*) FILTER (WHERE state NOT IN ('RESOLVED', 'CLOSED', 'MERGED_DUPLICATE')) AS open_requests_count,
    COUNT(*) FILTER (WHERE state = 'BLOCKED_PARTS') AS blocked_by_parts_count,
    COUNT(*) FILTER (WHERE sla_breached = TRUE) AS sla_breached_count,
    ROUND(
        100.0 * COUNT(*) FILTER (WHERE sla_breached = FALSE AND state IN ('RESOLVED', 'CLOSED')) /
        NULLIF(COUNT(*) FILTER (WHERE state IN ('RESOLVED', 'CLOSED')), 0), 2
    ) AS sla_compliance_percentage
FROM work_orders;
CREATE OR REPLACE VIEW v_recurring_incidents AS
SELECT
    cn.node_code,
    cn.name AS asset_or_room_name,
    wo.category,
    COUNT(wo.id) AS incident_count_30d,
    MAX(wo.created_at) AS last_incident_at
FROM work_orders wo
JOIN campus_nodes cn ON wo.target_node_id = cn.id
WHERE wo.created_at >= NOW() - INTERVAL '30 days'
  AND wo.state <> 'MERGED_DUPLICATE'
GROUP BY cn.node_code, cn.name, wo.category
HAVING COUNT(wo.id) >= 2
ORDER BY incident_count_30d DESC;
CREATE OR REPLACE VIEW v_staff_utilization AS
SELECT
    u.id AS tech_id,
    u.full_name,
    u.is_available,
    u.active_workload_count,
    u.max_concurrent_workload,
    ROUND(100.0 * u.active_workload_count / NULLIF(u.max_concurrent_workload, 0), 1) AS utilization_pct
FROM users u
WHERE u.role = 'TECHNICIAN';
CREATE OR REPLACE VIEW v_inventory_shortages AS
SELECT
    id, sku, name, category, physical_on_hand_qty, available_qty, reserved_qty, reorder_threshold, unit_cost
FROM inventory_parts
WHERE available_qty <= reorder_threshold;
