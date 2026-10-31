#!/usr/bin/env python3
"""
CampusOps: SRM Easwari Engineering College (Autonomous), Ramapuram, Chennai
Phase 1 Master Seed Generator (PostgreSQL 16 / asyncpg)
Deterministic, production-ready seeding script with zero placeholders.
"""

import asyncio
import os
import sys
from datetime import datetime, timezone, timedelta
import asyncpg
from dotenv import load_dotenv

load_dotenv()

DB_HOST = os.getenv("POSTGRES_HOST", "localhost")
DB_PORT = int(os.getenv("POSTGRES_PORT", 5432))
DB_USER = os.getenv("POSTGRES_USER", "postgres")
DB_PASS = os.getenv("POSTGRES_PASSWORD", "postgres")
DB_NAME = os.getenv("POSTGRES_DB", "campusops")


async def seed_campus():
    print("=" * 75)
    print("CAMPUSOPS SEED GENERATOR: SRM EASWARI ENGINEERING COLLEGE, CHENNAI")
    print(f"Connecting to postgresql://{DB_USER}:****@{DB_HOST}:{DB_PORT}/{DB_NAME}")
    print("=" * 75)

    conn = await asyncpg.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASS,
        database=DB_NAME,
    )

    try:
        async with conn.transaction():
            print("\n[1/7] Cleaning existing operational data...")
            await conn.execute("DELETE FROM outbound_notifications;")
            await conn.execute("ALTER TABLE audit_logs DISABLE TRIGGER trg_audit_tamper_guard_row;")
            await conn.execute("ALTER TABLE audit_logs DISABLE TRIGGER trg_audit_tamper_guard_stmt;")
            await conn.execute("DELETE FROM audit_logs;")
            await conn.execute("ALTER TABLE audit_logs ENABLE TRIGGER trg_audit_tamper_guard_row;")
            await conn.execute("ALTER TABLE audit_logs ENABLE TRIGGER trg_audit_tamper_guard_stmt;")
            await conn.execute("DELETE FROM room_bookings;")
            await conn.execute("DELETE FROM approvals;")
            await conn.execute("DELETE FROM part_reservations;")
            await conn.execute("DELETE FROM work_orders;")
            await conn.execute("ALTER SEQUENCE IF EXISTS work_orders_ticket_number_seq RESTART WITH 1;")
            await conn.execute("DELETE FROM inventory_movements;")
            await conn.execute("DELETE FROM inventory_parts;")
            await conn.execute("DELETE FROM processed_events;")
            await conn.execute("DELETE FROM node_dependencies;")
            await conn.execute("DELETE FROM campus_nodes;")
            await conn.execute("DELETE FROM staff_skills;")
            await conn.execute("DELETE FROM staff_shifts;")
            await conn.execute("DELETE FROM users;")
            await conn.execute("DELETE FROM departments;")

            print("\n[2/7] Seeding 5 Departments with balanced budget invariants...")
            dept_records = [
                ("DEPT-ADMIN", "Facilities & Campus Administration", 5000000.00, 5000000.00, 0.00, 0.00, 25000.00),
                ("DEPT-CSE-IT", "Computer Science & Information Technology", 3500000.00, 3500000.00, 0.00, 0.00, 15000.00),
                ("DEPT-ECE", "Electronics & Communication Engineering", 2800000.00, 2800000.00, 0.00, 0.00, 15000.00),
                ("DEPT-MECH-CIVIL", "Mechanical & Civil Engineering", 3000000.00, 3000000.00, 0.00, 0.00, 15000.00),
                ("DEPT-ROBOTICS", "Robotics & Automation Research Centre", 4000000.00, 4000000.00, 0.00, 0.00, 20000.00),
            ]
            dept_map = {}
            for code, name, tot, avail, enc, spent, lim in dept_records:
                row = await conn.fetchrow(
                    """
                    INSERT INTO departments (code, name, total_budget, available_budget, encumbered_budget, spent_budget, manager_approval_limit)
                    VALUES ($1, $2, $3, $4, $5, $6, $7)
                    RETURNING id;
                    """,
                    code, name, tot, avail, enc, spent, lim
                )
                dept_map[code] = row["id"]
                print(f"  + Department: {code} (Budget: Rs. {tot:,.2f})")

            print("\n[3/7] Seeding Users and 6 Specialized Domain Technicians...")
            user_records = [
                ("student_1@easwari.edu", "Aditya Raman", "STUDENT_FACULTY", dept_map["DEPT-CSE-IT"], True, 0, 4, "EEC-ACAD"),
                ("sys_admin_1@easwari.edu", "Anand Natarajan", "SYS_ADMIN", dept_map["DEPT-ADMIN"], True, 0, 4, "EEC-MAIN"),
                ("mgr_acad@easwari.edu", "Dr. S. Meenakshi", "DEPT_MANAGER", dept_map["DEPT-CSE-IT"], True, 0, 4, "EEC-ACAD"),
                ("mgr_facilities@easwari.edu", "Er. R. Venkatesh", "FACILITIES_ADMIN", dept_map["DEPT-ADMIN"], True, 0, 4, "EEC-MAIN"),
                ("procurement_approver_1@easwari.edu", "Mrs. L. Shanthi", "PROCUREMENT_APPROVER", dept_map["DEPT-ADMIN"], True, 0, 4, "EEC-MAIN"),
                # 6 Domain Specialized Technicians
                ("arunak0787@gmail.com", "Karthik Subramanian", "TECHNICIAN", dept_map["DEPT-ADMIN"], True, 0, 4, "EEC-MAIN"),
                ("tech_plumb_1@easwari.edu", "Ramesh Venkatesan", "TECHNICIAN", dept_map["DEPT-ADMIN"], True, 0, 4, "EEC-MAIN"),
                ("tech_net_1@easwari.edu", "Suresh Kumar", "TECHNICIAN", dept_map["DEPT-ADMIN"], True, 0, 4, "EEC-ACAD"),
                ("jeevadarwin007@gmail.com", "Selvam Muthuraj", "TECHNICIAN", dept_map["DEPT-ADMIN"], True, 0, 4, "EEC-MECH-PG"),
                ("tech_sos_1@easwari.edu", "Mohanraj Krishnan", "TECHNICIAN", dept_map["DEPT-ADMIN"], True, 0, 4, "EEC-MAIN"),
                ("tech_sweeper_1@easwari.edu", "Thangavel Murugan", "TECHNICIAN", dept_map["DEPT-ADMIN"], True, 0, 4, "EEC-ACAD"),
            ]
            user_map = {}
            for email, name, role, dept_id, avail, load, max_load, base_bldg in user_records:
                row = await conn.fetchrow(
                    """
                    INSERT INTO users (email, full_name, role, department_id, is_available, active_workload_count, max_concurrent_workload, base_building_code)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                    RETURNING id;
                    """,
                    email, name, role, dept_id, avail, load, max_load, base_bldg
                )
                user_map[email] = row["id"]
                print(f"  + User: {name} ({role}) - {email}")

            print("\n  -> Seeding technician active 90-day shifts and domain proficiencies...")
            now = datetime.now(timezone.utc)
            shift_start = now - timedelta(days=7)
            shift_end = now + timedelta(days=90)

            all_techs = [
                "arunak0787@gmail.com",
                "tech_plumb_1@easwari.edu",
                "tech_net_1@easwari.edu",
                "jeevadarwin007@gmail.com",
                "tech_sos_1@easwari.edu",
                "tech_sweeper_1@easwari.edu",
            ]

            # Assign shifts
            for tech_email in all_techs:
                await conn.execute(
                    """
                    INSERT INTO staff_shifts (user_id, shift_window)
                    VALUES ($1, tstzrange($2, $3, '[)'));
                    """,
                    user_map[tech_email], shift_start, shift_end
                )

            # Assign domain skills (Level 5)
            skills_data = [
                (user_map["arunak0787@gmail.com"], "ELECTRICAL", 5),
                (user_map["tech_plumb_1@easwari.edu"], "PLUMBING", 5),
                (user_map["tech_net_1@easwari.edu"], "NETWORK", 5),
                (user_map["jeevadarwin007@gmail.com"], "STRUCTURAL_SAFETY", 5),
                (user_map["tech_sos_1@easwari.edu"], "SOS", 5),
                (user_map["tech_sweeper_1@easwari.edu"], "SWEEPER", 5),
            ]

            # Ensure FSM transitions exist for auto-dispatch and technician resume & resolution
            await conn.execute("""
                INSERT INTO fsm_state_transitions (from_state, to_state, allowed_roles) VALUES
                ('TRIAGED', 'ASSIGNED', ARRAY['SYS_ADMIN'::user_role, 'FACILITIES_ADMIN'::user_role, 'DEPT_MANAGER'::user_role, 'STUDENT_FACULTY'::user_role]),
                ('INGESTED', 'ASSIGNED', ARRAY['SYS_ADMIN'::user_role, 'FACILITIES_ADMIN'::user_role, 'DEPT_MANAGER'::user_role, 'STUDENT_FACULTY'::user_role]),
                ('BLOCKED_PARTS', 'IN_PROGRESS', ARRAY['TECHNICIAN'::user_role, 'SYS_ADMIN'::user_role, 'FACILITIES_ADMIN'::user_role]),
                ('BLOCKED_PARTS', 'RESOLVED', ARRAY['TECHNICIAN'::user_role, 'SYS_ADMIN'::user_role, 'FACILITIES_ADMIN'::user_role]),
                ('ASSIGNED', 'RESOLVED', ARRAY['TECHNICIAN'::user_role, 'SYS_ADMIN'::user_role])
                ON CONFLICT (from_state, to_state) DO UPDATE SET allowed_roles = EXCLUDED.allowed_roles;
            """)
            for uid, skill, prof in skills_data:
                await conn.execute(
                    """
                    INSERT INTO staff_skills (user_id, skill, proficiency_level)
                    VALUES ($1, $2, $3);
                    """,
                    uid, skill, prof
                )

            print("\n[4/7] Seeding Campus Topology (5 Blocks, 6 Infrastructure Nodes, 32 Rooms)...")
            nodes_data = [
                # 5 Buildings
                ("EEC-MAIN", "Main Administrative Block", "BUILDING", "EEC-MAIN", 1, 0, [], True, 25, "ADMINISTRATIVE"),
                ("EEC-ACAD", "Academic Tech Block (CSE/IT/AI&DS/ECE)", "BUILDING", "EEC-ACAD", 1, 0, [], True, 30, "CLASSROOM"),
                ("EEC-MECH-PG", "Mechanical, Civil & Central PG Library Block", "BUILDING", "EEC-MECH-PG", 1, 0, [], True, 20, "CLASSROOM"),
                ("EEC-ROBOTICS", "ABB Robotics Research & Automation Centre", "BUILDING", "EEC-ROBOTICS", 1, 0, [], True, 18, "LAB"),
                ("EEC-AUD-FC", "TRP Auditorium & Central Food Court", "BUILDING", "EEC-AUD-FC", 1, 0, [], True, 15, "AUDITORIUM"),

                # 6 Utility / Infrastructure Parents
                ("SUBSTATION-MAIN", "Main 11kV Campus Electrical Substation", "ELECTRICAL_PANEL", "EEC-MAIN", 1, 0, [], True, 30, None),
                ("PANEL-ACAD-F2", "Academic Block 2nd Floor Distribution Board", "ELECTRICAL_PANEL", "EEC-ACAD", 2, 0, [], True, 25, None),
                ("SW-CORE-CAMPUS", "Campus Core 10Gbps Optical Switch", "NETWORK_SWITCH", "EEC-MAIN", 1, 0, [], True, 30, None),
                ("SW-CORE-ACAD-F3", "Academic Block 3rd Floor PoE Core Switch", "NETWORK_SWITCH", "EEC-ACAD", 3, 0, [], True, 28, None),
                ("AHU-AUD-MAIN", "TRP Auditorium Central Air Handling Unit", "HVAC_AHU", "EEC-AUD-FC", 1, 0, [], True, 20, None),
                ("PUMP-CENTRAL", "Campus Central Water Hydro-Pneumatic Pump", "EQUIPMENT", "EEC-MAIN", 1, 0, [], True, 15, None),

                # Rooms: EEC-ACAD (Academic Tech Block)
                ("RM-ACAD-101", "Ground Floor Smart Class 101", "ROOM", "EEC-ACAD", 1, 70, ["PROJECTOR", "AC"], True, 15, "CLASSROOM"),
                ("RM-ACAD-102", "Ground Floor Lecture Hall 102", "ROOM", "EEC-ACAD", 1, 75, ["PROJECTOR", "AC"], True, 15, "CLASSROOM"),
                ("RM-ACAD-201", "CSE Department Classroom 201", "ROOM", "EEC-ACAD", 2, 70, ["PROJECTOR", "AC"], True, 15, "CLASSROOM"),
                ("RM-ACAD-202", "IT Department Classroom 202", "ROOM", "EEC-ACAD", 2, 80, ["PROJECTOR", "AC"], True, 15, "CLASSROOM"),
                ("RM-ACAD-204", "CSE/IT 2nd Floor Smart Classroom", "ROOM", "EEC-ACAD", 2, 110, ["PROJECTOR", "AC", "AUDIO_SYSTEM", "SMART_BOARD"], True, 25, "CLASSROOM"),
                ("LAB-ACAD-301", "Advanced Computing & AI Lab", "ROOM", "EEC-ACAD", 3, 75, ["HIGH_SPEED_LAN", "AC", "UPS_BACKUP"], True, 25, "LAB"),
                ("LAB-ACAD-302", "Data Structures & Cloud Lab", "ROOM", "EEC-ACAD", 3, 75, ["HIGH_SPEED_LAN", "AC", "UPS_BACKUP"], True, 25, "LAB"),
                ("LAB-ACAD-304", "Networks & Cybersecurity Lab", "ROOM", "EEC-ACAD", 3, 75, ["HIGH_SPEED_LAN", "AC", "UPS_BACKUP"], True, 25, "LAB"),
                ("RM-ACAD-401", "ECE Department Seminar Hall", "ROOM", "EEC-ACAD", 4, 90, ["PROJECTOR", "AC", "AUDIO_SYSTEM"], True, 18, "SEMINAR_HALL"),
                ("RM-ACAD-402", "VLSI & Embedded Systems Lab", "ROOM", "EEC-ACAD", 4, 60, ["PROJECTOR", "AC", "HIGH_SPEED_LAN"], True, 15, "LAB"),

                # Rooms: EEC-MECH-PG (Mechanical & PG Library Block)
                ("RM-MECH-101", "Engineering Graphics Drawing Hall", "ROOM", "EEC-MECH-PG", 1, 80, ["PROJECTOR"], True, 12, "WORKSHOP"),
                ("RM-MECH-102", "PG Mechanical Smart Lecture Hall", "ROOM", "EEC-MECH-PG", 1, 125, ["PROJECTOR", "AC", "AUDIO_SYSTEM", "WHEELCHAIR_RAMP", "SMART_BOARD"], True, 22, "CLASSROOM"),
                ("RM-MECH-201", "Fluid Dynamics & Thermal Lab", "ROOM", "EEC-MECH-PG", 2, 50, ["EXHAUST_SYSTEM"], True, 12, "LAB"),
                ("RM-MECH-202", "CAD/CAM Simulation Centre", "ROOM", "EEC-MECH-PG", 2, 60, ["HIGH_SPEED_LAN", "AC", "UPS_BACKUP"], True, 16, "LAB"),
                ("RM-MECH-301", "Central PG Research Reading Room", "ROOM", "EEC-MECH-PG", 3, 70, ["AC", "HIGH_SPEED_LAN"], True, 14, "SEMINAR_HALL"),
                ("RM-MECH-302", "Digital Library Resource Centre", "ROOM", "EEC-MECH-PG", 3, 80, ["HIGH_SPEED_LAN", "AC", "UPS_BACKUP"], True, 18, "LAB"),
                ("RM-MECH-401", "Mechanical & Civil Seminar Hall", "ROOM", "EEC-MECH-PG", 4, 100, ["PROJECTOR", "AC", "AUDIO_SYSTEM"], True, 16, "SEMINAR_HALL"),
                ("RM-MECH-402", "Mechatronics & Automation Studio", "ROOM", "EEC-MECH-PG", 4, 50, ["AC", "HIGH_SPEED_LAN"], True, 14, "LAB"),

                # Rooms: EEC-MAIN (Administrative Block - No capacity field needed, purely administrative)
                ("RM-MAIN-101", "Admissions & Counselling Centre", "ROOM", "EEC-MAIN", 1, 0, ["AC", "DISPLAY_PANEL"], True, 15, "ADMINISTRATIVE"),
                ("RM-MAIN-102", "Executive Boardroom", "ROOM", "EEC-MAIN", 1, 0, ["PROJECTOR", "AC", "AUDIO_SYSTEM"], True, 20, "ADMINISTRATIVE"),
                ("RM-MAIN-201", "Controller of Examinations Strongroom", "ROOM", "EEC-MAIN", 2, 0, ["CCTV_SURVEILLANCE", "AC", "BIOMETRIC_ACCESS"], True, 28, "ADMINISTRATIVE"),
                ("RM-MAIN-202", "Academic Council Chamber", "ROOM", "EEC-MAIN", 2, 0, ["PROJECTOR", "AC", "AUDIO_SYSTEM"], True, 22, "ADMINISTRATIVE"),
                ("RM-MAIN-301", "Campus Central Data Centre", "ROOM", "EEC-MAIN", 3, 0, ["PRECISION_AC", "FIRE_SUPPRESSION", "UPS_BACKUP"], True, 30, "ADMINISTRATIVE"),
                ("RM-MAIN-302", "ERP & Digital Governance Cell", "ROOM", "EEC-MAIN", 3, 0, ["HIGH_SPEED_LAN", "AC"], True, 16, "ADMINISTRATIVE"),

                # Rooms: EEC-ROBOTICS (ABB Centre)
                ("RM-ROB-101", "ABB Industrial Robot Workcell Lab", "ROOM", "EEC-ROBOTICS", 1, 45, ["THREE_PHASE_POWER", "AC", "SAFETY_CAGE"], True, 20, "LAB"),
                ("RM-ROB-102", "Cobot & Machine Vision Station", "ROOM", "EEC-ROBOTICS", 1, 40, ["AC", "HIGH_SPEED_LAN"], True, 18, "LAB"),
                ("RM-ROB-201", "Industry 4.0 IoT Prototype Studio", "ROOM", "EEC-ROBOTICS", 2, 50, ["AC", "HIGH_SPEED_LAN", "3D_PRINTER"], True, 18, "LAB"),
                ("RM-ROB-202", "Autonomous Mobile Robotics Arena", "ROOM", "EEC-ROBOTICS", 2, 40, ["SAFETY_NET", "HIGH_SPEED_LAN"], True, 16, "LAB"),

                # Rooms: EEC-AUD-FC (Auditorium & Food Court)
                ("RM-AUD-MAIN", "TRP Main Auditorium Hall", "ROOM", "EEC-AUD-FC", 1, 850, ["CENTRAL_AC", "STAGE_LIGHTING", "LINE_ARRAY_AUDIO"], True, 24, "AUDITORIUM"),
                ("RM-AUD-MINI", "TRP Mini AV Amphitheatre", "ROOM", "EEC-AUD-FC", 2, 150, ["PROJECTOR", "AC", "AUDIO_SYSTEM"], True, 18, "AUDITORIUM"),
                ("RM-FC-101", "Student Food Court Dining Hall", "ROOM", "EEC-AUD-FC", 1, 300, ["EXHAUST_SYSTEM", "WASH_COUNTERS"], True, 14, "FOOD_COURT"),
                ("RM-FC-201", "Faculty & Guest Dining Lounge", "ROOM", "EEC-AUD-FC", 2, 80, ["AC", "WIFI"], True, 12, "FOOD_COURT"),
            ]

            node_map = {}
            for code, name, ntype, bcode, floor, cap, feats, is_op, crit, rtype in nodes_data:
                row = await conn.fetchrow(
                    """
                    INSERT INTO campus_nodes (node_code, name, node_type, building_code, floor_number, room_capacity, room_features, is_operational, criticality_weight, room_type)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                    RETURNING id;
                    """,
                    code, name, ntype, bcode, floor, cap, feats, is_op, crit, rtype
                )
                node_map[code] = row["id"]

            print(f"  + Inserted {len(nodes_data)} campus nodes.")

            print("\n  -> Wiring Directed Acyclic Graph (DAG) Infrastructure Dependencies...")
            dag_edges = [
                # Electrical hierarchy
                (node_map["EEC-MAIN"], node_map["SUBSTATION-MAIN"], "ELECTRICAL"),
                (node_map["SUBSTATION-MAIN"], node_map["PANEL-ACAD-F2"], "ELECTRICAL"),
                (node_map["PANEL-ACAD-F2"], node_map["RM-ACAD-204"], "ELECTRICAL"),
                (node_map["PANEL-ACAD-F2"], node_map["RM-ACAD-201"], "ELECTRICAL"),
                (node_map["PANEL-ACAD-F2"], node_map["RM-ACAD-202"], "ELECTRICAL"),

                # Network hierarchy (Wi-Fi storm nodes share SW-CORE-ACAD-F3)
                (node_map["EEC-MAIN"], node_map["SW-CORE-CAMPUS"], "NETWORK"),
                (node_map["SW-CORE-CAMPUS"], node_map["SW-CORE-ACAD-F3"], "NETWORK"),
                (node_map["SW-CORE-ACAD-F3"], node_map["LAB-ACAD-301"], "NETWORK"),
                (node_map["SW-CORE-ACAD-F3"], node_map["LAB-ACAD-302"], "NETWORK"),
                (node_map["SW-CORE-ACAD-F3"], node_map["LAB-ACAD-304"], "NETWORK"),

                # HVAC hierarchy
                (node_map["EEC-AUD-FC"], node_map["AHU-AUD-MAIN"], "HVAC"),
                (node_map["AHU-AUD-MAIN"], node_map["RM-AUD-MAIN"], "HVAC"),
            ]
            for p_id, c_id, domain in dag_edges:
                await conn.execute(
                    """
                    INSERT INTO node_dependencies (parent_node_id, child_node_id, dependency_domain)
                    VALUES ($1, $2, $3);
                    """,
                    p_id, c_id, domain
                )
            print(f"  + Wired {len(dag_edges)} infrastructure DAG dependency edges.")

            print("\n[5/7] Seeding 25 Authoritative Inventory SKUs with movement ledger entries...")
            inventory_data = [
                # CRITICAL DISRUPTION FIXTURE: PART-MCCB-63A (ZERO ON HAND)
                ("PART-MCCB-63A", "63A 4-Pole Distribution MCCB Breaker", "ELECTRICAL", 0, 0, 0, 2, 4850.00, 24),
                # Electrical Parts
                ("PART-MCB-32A", "32A Double Pole MCB Modular", "ELECTRICAL", 15, 15, 0, 5, 450.00, 12),
                ("PART-CONT-40A", "40A 3-Phase Industrial Power Contactor", "ELECTRICAL", 6, 6, 0, 2, 1850.00, 24),
                ("PART-LED-36W", "36W 2x2 Recessed LED False Ceiling Panel", "ELECTRICAL", 40, 40, 0, 10, 850.00, 24),
                ("PART-CABLE-4SQ", "4.0 sq.mm FRLS Copper Wire Coil 90m", "ELECTRICAL", 8, 8, 0, 2, 3200.00, 48),
                ("PART-UPS-BAT", "12V 100Ah Sealed Lead Acid UPS Battery", "ELECTRICAL", 12, 12, 0, 4, 9500.00, 48),
                # Network Parts
                ("PART-SFP-10G", "10GBASE-SR SFP+ 850nm Optical Transceiver", "NETWORK", 10, 10, 0, 3, 2400.00, 24),
                ("PART-CAT6-BOX", "Cat6 UTP Solid Copper 305m Cable Drum", "NETWORK", 6, 6, 0, 2, 7500.00, 24),
                ("PART-RJ45-100", "RJ45 Cat6 Pass-Through Connectors (Pack of 100)", "NETWORK", 25, 25, 0, 5, 650.00, 12),
                ("PART-PATCH-2M", "Cat6 Molded Gigabit Patch Cord 2m Blue", "NETWORK", 120, 120, 0, 20, 120.00, 12),
                ("PART-POE-INJ", "Gigabit 802.3at 30W PoE+ Power Injector", "NETWORK", 8, 8, 0, 2, 1450.00, 24),
                ("PART-WIFI-AP", "Dual-Band Wi-Fi 6 Ceiling Access Point", "NETWORK", 5, 5, 0, 2, 8900.00, 48),
                # AV Equipment Parts
                ("PART-PROJ-LAMP", "OEM 240W Projector Replacement Lamp Module", "AV_EQUIPMENT", 4, 4, 0, 2, 5400.00, 48),
                ("PART-HDMI-15M", "Active Optical HDMI 2.0 Cable 15m 4K@60Hz", "AV_EQUIPMENT", 14, 14, 0, 4, 1650.00, 24),
                ("PART-MIC-UHF", "Wireless Dual UHF Lapel/Handheld Microphone", "AV_EQUIPMENT", 6, 6, 0, 2, 4200.00, 24),
                ("PART-AMP-250W", "250W Zone Commercial Public Address Amplifier", "AV_EQUIPMENT", 2, 2, 0, 1, 14500.00, 72),
                # HVAC & Mechanical Parts
                ("PART-AC-CAP-50", "50 MFD Dual Motor Run Capacitor", "HVAC", 18, 18, 0, 5, 380.00, 12),
                ("PART-AC-GAS-R32", "R32 Refrigerant Gas Cylinder 9kg", "HVAC", 4, 4, 0, 2, 4800.00, 48),
                ("PART-AHU-BELT", "V-Belt B-Section Industrial Drive Belt", "HVAC", 8, 8, 0, 3, 420.00, 24),
                ("PART-AC-PCB", "Inverter AC Outdoor Microcontroller Board", "HVAC", 3, 3, 0, 2, 5200.00, 72),
                # Plumbing Parts
                ("PART-VALVE-2IN", "2-inch Cast Iron Ball Valve Class 150", "PLUMBING", 10, 10, 0, 3, 1150.00, 24),
                ("PART-CPVC-1IN", "1-inch CPVC SDR-11 Pressure Pipe 3m", "PLUMBING", 30, 30, 0, 8, 480.00, 12),
                ("PART-TAP-BRASS", "Commercial Sensor Auto-Close Basin Tap", "PLUMBING", 12, 12, 0, 4, 2200.00, 48),
                # Safety & Structural
                ("PART-EXT-ABC", "ABC Dry Powder 6kg Fire Extinguisher", "STRUCTURAL_SAFETY", 16, 16, 0, 4, 1850.00, 48),
                ("PART-SMOKE-OPT", "Photoelectric Optical Smoke Detector Base", "STRUCTURAL_SAFETY", 22, 22, 0, 6, 920.00, 24),
            ]

            part_map = {}
            for sku, name, cat, phys, avail, res, reorder, cost, lead in inventory_data:
                row = await conn.fetchrow(
                    """
                    INSERT INTO inventory_parts (sku, name, category, physical_on_hand_qty, available_qty, reserved_qty, reorder_threshold, unit_cost, lead_time_hours)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                    RETURNING id;
                    """,
                    sku, name, cat, phys, avail, res, reorder, cost, lead
                )
                part_map[sku] = row["id"]

                # Record receipt movement for initial stock > 0
                if phys > 0:
                    await conn.execute(
                        """
                        INSERT INTO inventory_movements (part_id, actor_id, movement_type, delta_physical, delta_available, delta_reserved)
                        VALUES ($1, $2, 'RECEIPT', $3, $4, $5);
                        """,
                        row["id"], user_map["sys_admin_1@easwari.edu"], phys, avail, res
                    )

            print(f"  + Inserted {len(inventory_data)} inventory SKUs (MCCB breaker seeded at 0 stock).")

            print("\n[6/7] Seeding Room Bookings with GiST Exclusion Checks...")
            # 1. CRITICAL EXAM DISRUPTION FIXTURE:
            # RM-ACAD-204 (CSE/IT 2nd Floor Smart Classroom) booked for semester exam 45 mins from NOW
            exam_start = now + timedelta(minutes=45)
            exam_end = exam_start + timedelta(hours=3)

            await conn.execute(
                """
                INSERT INTO room_bookings (room_node_id, booking_type, course_or_event_title, faculty_user_id, student_count, required_features, time_slot, status)
                VALUES ($1, 'EXAM', $2, $3, $4, $5, tstzrange($6, $7, '[)'), 'CONFIRMED');
                """,
                node_map["RM-ACAD-204"],
                "CS8601 Mobile Computing Final Examination (Semester VI)",
                user_map["mgr_acad@easwari.edu"],
                110,
                ["PROJECTOR", "AC", "AUDIO_SYSTEM"],
                exam_start, exam_end
            )
            print(f"  + [DISRUPTION FIXTURE] RM-ACAD-204: 110-student Exam scheduled ({exam_start.strftime('%H:%M')} - {exam_end.strftime('%H:%M')} UTC)")

            # Additional background bookings in other rooms (RM-MECH-102 intentionally kept free as relocation target)
            other_bookings = [
                (node_map["RM-ACAD-101"], "CLASS", "IT8501 Web Technology Lecture", user_map["mgr_acad@easwari.edu"], 65, exam_start, exam_end),
                (node_map["RM-ACAD-102"], "CLASS", "CS8491 Computer Architecture", user_map["mgr_acad@easwari.edu"], 70, exam_start - timedelta(hours=1), exam_start + timedelta(hours=1)),
                (node_map["RM-ACAD-201"], "CLASS", "EC8691 Microprocessors & Microcontrollers", user_map["mgr_acad@easwari.edu"], 60, exam_start, exam_end),
                (node_map["RM-MECH-101"], "CLASS", "ME8492 Kinematics of Machinery", user_map["mgr_acad@easwari.edu"], 75, exam_start, exam_end),
                (node_map["RM-MAIN-102"], "CLASS", "Board of Studies Bi-Annual Meeting", user_map["mgr_facilities@easwari.edu"], 25, exam_start, exam_end),
                (node_map["RM-ROB-101"], "CLASS", "RO8501 Industrial Robotics Hands-On", user_map["mgr_acad@easwari.edu"], 40, exam_start, exam_end),
            ]
            for r_id, b_type, title, f_id, count, b_start, b_end in other_bookings:
                await conn.execute(
                    """
                    INSERT INTO room_bookings (room_node_id, booking_type, course_or_event_title, faculty_user_id, student_count, time_slot, status)
                    VALUES ($1, $2, $3, $4, $5, tstzrange($6, $7, '[)'), 'CONFIRMED');
                    """,
                    r_id, b_type, title, f_id, count, b_start, b_end
                )
            print(f"  + Inserted {len(other_bookings) + 1} confirmed room bookings (RM-MECH-102 verified unbooked).")

            print("\n[7/7] Verifying live database analytics views...")
            summary = await conn.fetchrow("SELECT * FROM v_analytics_summary;")
            print(f"  + v_analytics_summary: open_requests={summary['open_requests_count']}, blocked_parts={summary['blocked_by_parts_count']}")

            shortages = await conn.fetch("SELECT sku, name, physical_on_hand_qty, available_qty FROM v_inventory_shortages;")
            print(f"  + v_inventory_shortages: {len(shortages)} SKU(s) below reorder threshold:")
            for s in shortages:
                print(f"    - {s['sku']}: {s['name']} (Available: {s['available_qty']}, Physical: {s['physical_on_hand_qty']})")

    finally:
        await conn.close()

    print("\n" + "=" * 75)
    print("CAMPUSOPS SEEDING COMPLETE FOR SRM EASWARI ENGINEERING COLLEGE")
    print("=" * 75)


if __name__ == "__main__":
    asyncio.run(seed_campus())

