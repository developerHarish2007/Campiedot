import json
import asyncio
import logging
from typing import Optional, Dict, Any, List
import httpx
from pydantic import BaseModel, Field
from app.config import settings

logger = logging.getLogger("campusops_ai_agents")

# Campus Topology Ground Truth for Anti-Hallucination Guard
VALID_BUILDING_CODES = {
    "EEC-MAIN": "Main Administrative Block",
    "EEC-ACAD": "Academic Tech Block (CSE/IT/AI&DS)",
    "EEC-MECH-PG": "Mechanical, Civil & Central PG Library",
    "EEC-ROBOTICS": "ABB Robotics Research & Automation",
    "EEC-AUD-FC": "TRP Auditorium & Food Court",
}

SAFE_ASSEMBLY_POINTS = [
    "EEC Central Sports Ground & Lawn Assembly Area A",
    "Main Administrative Quadrangle Open Area B",
    "Mechanical Block Open Grounds Area C",
]

EMERGENCY_CONTACTS = [
    {"role": "Campus Security & Fire Control", "phone": "+91 44 2249 0853", "extension": "100"},
    {"role": "Campus Health & Medical Centre", "phone": "+91 44 2249 0850", "extension": "108"},
    {"role": "Chennai Fire & Rescue Services", "phone": "101", "extension": "Emergency"},
]


# ==============================================================================
# SCHEMAS
# ==============================================================================

class WorkerDispatchEmailSchema(BaseModel):
    subject: str
    html_body: str
    text_body: str
    tools_needed: List[str] = Field(default_factory=list)
    safety_precautions: List[str] = Field(default_factory=list)


class EmergencyInstructionsSchema(BaseModel):
    is_emergency: bool = False
    threat_level: str = "STANDARD"  # CRITICAL_HAZARD, HIGH_ALERT, STANDARD
    hazard_type: Optional[str] = None  # FIRE, GAS_LEAK, ELECTRICAL_EXPLOSION, STRUCTURAL_COLLAPSE, OTHER
    headline: str
    target_building: str
    immediate_actions: List[str] = Field(default_factory=list)
    evacuation_route: str
    assembly_point: str
    emergency_contacts: List[Dict[str, str]] = Field(default_factory=list)


class VerificationAuditResult(BaseModel):
    verified: bool
    hallucinations_detected: List[str] = Field(default_factory=list)
    corrections_applied: List[str] = Field(default_factory=list)
    sanitized_output: Dict[str, Any]


# ==============================================================================
# AGENT 1: WORKER DISPATCH EMAIL AGENT
# ==============================================================================

WORKER_DISPATCH_PROMPT = """You are the Worker Dispatch AI Agent for SRM Easwari Engineering College CampusOps.
A maintenance problem has been assigned to a worker (such as an Electrician or Plumber).
Your task is to generate a comprehensive, highly actionable email notification to the worker.

Return ONLY a valid JSON object with:
- "subject": Clear, concise subject line with ticket number, urgency level, and concise issue.
- "html_body": Well-formatted, responsive HTML email containing:
    * Incident overview, ticket number, and priority badge
    * Location (Building, Floor, Room Code/Name)
    * Specific reported problem and symptoms
    * Action items checklist tailored to the worker's trade (e.g. pipe wrench/sealant for Plumber, multimeter/insulated screwdrivers for Electrician)
    * Critical safety warnings (e.g. shut off main valve, isolate circuit breaker)
- "text_body": Plain text equivalent of the email
- "tools_needed": List of 3-5 specific tools or materials required
- "safety_precautions": List of 2-3 specific safety precautions

Ground all information strictly in the reported problem details. Do NOT invent details."""


class WorkerDispatchAgent:
    @staticmethod
    async def generate_dispatch_email(
        ticket_number: int,
        category: str,
        raw_description: str,
        location_hint: Optional[str],
        worker_name: str,
        worker_role: str,
        urgency: str = "P2_MEDIUM"
    ) -> WorkerDispatchEmailSchema:
        """Generates worker notification email using Groq with deterministic fallback."""
        loc_str = location_hint or "Campus Facility (General)"
        prompt_input = (
            f"Ticket Number: #{ticket_number}\n"
            f"Category / Domain: {category}\n"
            f"Worker Name: {worker_name}\n"
            f"Worker Role/Trade: {worker_role}\n"
            f"Location: {loc_str}\n"
            f"Urgency: {urgency}\n"
            f"Reported Problem:\n{raw_description}"
        )

        if settings.GROQ_API_KEY:
            try:
                headers = {
                    "Authorization": f"Bearer {settings.GROQ_API_KEY}",
                    "Content-Type": "application/json",
                }
                payload = {
                    "model": settings.GROQ_MODEL,
                    "messages": [
                        {"role": "system", "content": WORKER_DISPATCH_PROMPT},
                        {"role": "user", "content": prompt_input}
                    ],
                    "response_format": {"type": "json_object"},
                    "temperature": 0.2,
                    "max_tokens": 1024,
                }
                async with httpx.AsyncClient(timeout=4.0) as client:
                    res = await client.post(settings.GROQ_API_URL, json=payload, headers=headers)
                    if res.status_code == 200:
                        content = res.json()["choices"][0]["message"]["content"]
                        parsed = json.loads(content)
                        return WorkerDispatchEmailSchema(
                            subject=parsed.get("subject") or f"[DISPATCH #{ticket_number}] {category} Work Order",
                            html_body=parsed.get("html_body") or f"<p>{raw_description}</p>",
                            text_body=parsed.get("text_body") or raw_description,
                            tools_needed=parsed.get("tools_needed") or [],
                            safety_precautions=parsed.get("safety_precautions") or []
                        )
            except Exception as e:
                logger.warning(f"Groq WorkerDispatchAgent failed: {e}. Using deterministic fallback.")

        # Deterministic Fallback Generator
        tools = ["Standard Technician Toolset", "Safety Gloves"]
        precautions = ["Verify safe physical access before starting work", "Report any uncontained hazards to control room"]
        if "PLUMB" in category.upper() or "PLUMB" in worker_role.upper():
            tools = ["Pipe Wrench", "Teflon Thread Seal Tape", "Replacement Washers/Valves", "Drain Snake"]
            precautions = ["Shut off localized water isolation valve before dismantling fixtures", "Check for standing water near electrical points"]
        elif "ELEC" in category.upper() or "ELEC" in worker_role.upper():
            tools = ["Digital Multimeter", "1000V Insulated Screwdrivers", "Wire Strippers", "Lockout/Tagout Kit"]
            precautions = ["Isolate distribution MCB breaker and confirm zero voltage with multimeter", "Wear rubber-insulated electrical safety boots"]
        elif "HVAC" in category.upper():
            tools = ["Pressure Manifold Gauges", "Refrigerant Leak Detector", "Fin Comb", "Hex Keys"]
            precautions = ["De-energize condensing unit before servicing fan motors", "Handle refrigerant cylinders in well-ventilated areas"]

        html_body = f"""
        <div style="font-family: Arial, sans-serif; background-color: #0f172a; color: #f8fafc; padding: 24px; border-radius: 8px;">
            <div style="border-bottom: 2px solid #3b82f6; padding-bottom: 12px; margin-bottom: 16px;">
                <h2 style="color: #60a5fa; margin: 0;">SRM Easwari Engineering College &bull; CampusOps</h2>
                <p style="color: #94a3b8; margin: 4px 0 0 0; font-size: 13px;">Maintenance Work Order Dispatch Notice</p>
            </div>
            
            <p>Dear <strong>{worker_name}</strong> ({worker_role}),</p>
            <p>You have been assigned to maintenance <strong>Ticket #{ticket_number}</strong>.</p>
            
            <div style="background-color: #1e293b; padding: 16px; border-radius: 6px; border-left: 4px solid #3b82f6; margin: 16px 0;">
                <table style="width: 100%; border-collapse: collapse; font-size: 13px;">
                    <tr><td style="color: #94a3b8; padding: 4px 0;"><strong>Location:</strong></td><td style="color: #f1f5f9;">{loc_str}</td></tr>
                    <tr><td style="color: #94a3b8; padding: 4px 0;"><strong>Category:</strong></td><td style="color: #f1f5f9;">{category}</td></tr>
                    <tr><td style="color: #94a3b8; padding: 4px 0;"><strong>Urgency Level:</strong></td><td style="color: #f87171;">{urgency}</td></tr>
                </table>
                <div style="margin-top: 12px; padding-top: 12px; border-top: 1px solid #334155;">
                    <strong style="color: #cbd5e1;">Reported Issue:</strong>
                    <p style="color: #e2e8f0; margin: 6px 0 0 0; font-style: italic;">"{raw_description}"</p>
                </div>
            </div>

            <h4 style="color: #38bdf8; margin: 16px 0 8px 0;">Recommended Tools & Materials:</h4>
            <ul style="color: #cbd5e1; font-size: 13px; margin: 0 0 16px 0; padding-left: 20px;">
                {''.join(f'<li>{t}</li>' for t in tools)}
            </ul>

            <h4 style="color: #fbbf24; margin: 16px 0 8px 0;">Safety Precautions:</h4>
            <ul style="color: #cbd5e1; font-size: 13px; margin: 0 0 16px 0; padding-left: 20px;">
                {''.join(f'<li>{p}</li>' for p in precautions)}
            </ul>

            <p style="color: #64748b; font-size: 11px; margin-top: 24px; border-top: 1px solid #334155; padding-top: 12px;">
                Automated dispatch via CampusOps AI &bull; SRM Easwari Engineering College (Autonomous), Ramapuram, Chennai.
            </p>
        </div>
        """

        text_body = (
            f"[CampusOps Dispatch] Ticket #{ticket_number} - {category}\n"
            f"Assigned to: {worker_name} ({worker_role})\n"
            f"Location: {loc_str}\n"
            f"Urgency: {urgency}\n\n"
            f"Issue: {raw_description}\n\n"
            f"Required Tools: {', '.join(tools)}\n"
            f"Safety: {', '.join(precautions)}\n"
        )

        return WorkerDispatchEmailSchema(
            subject=f"[DISPATCH #{ticket_number}] {category} Work Order at {loc_str}",
            html_body=html_body,
            text_body=text_body,
            tools_needed=tools,
            safety_precautions=precautions
        )


# ==============================================================================
# AGENT 2: EMERGENCY SAFETY INSTRUCTION AGENT
# ==============================================================================

INSTRUCTION_AGENT_PROMPT = """You are the Campus Emergency Safety Instruction AI Agent for SRM Easwari Engineering College.
When a severe life-safety threat, disaster, or fast-spreading hazard (such as a fire, electrical explosion, chemical/gas leak, or structural collapse) occurs:
Your task is to generate immediate, authoritative, crystal-clear life-safety evacuation instructions for students, faculty, and staff in that building/floor to safely escape and assemble.

The instructions MUST be strictly grounded in SRM Easwari campus layout:
- Known Building Blocks: EEC-MAIN (Main Administrative Block), EEC-ACAD (Academic Tech Block), EEC-MECH-PG (Mechanical & Civil Block), EEC-ROBOTICS (Robotics Research Block), EEC-AUD-FC (Auditorium & Food Court).
- Safe Assembly Points: "EEC Central Sports Ground & Lawn Assembly Area A", "Main Administrative Quadrangle Open Area B".
- Evacuation Routes: Use exterior staircases; NEVER use elevators during fire, smoke, or structural emergencies.

Return ONLY a valid JSON object with:
- "is_emergency": true
- "threat_level": "CRITICAL_HAZARD" or "HIGH_ALERT"
- "hazard_type": "FIRE", "GAS_LEAK", "ELECTRICAL_EXPLOSION", "STRUCTURAL_COLLAPSE", or "OTHER"
- "headline": Short urgent banner headline (e.g. "🚨 CRITICAL FIRE ALERT: EVACUATE ACADEMIC TECH BLOCK IMMEDIATELY")
- "target_building": Building code and name
- "immediate_actions": List of 4-5 numbered, step-by-step immediate safety actions
- "evacuation_route": Specific route description using staircases to ground
- "assembly_point": Safe assembly point
- "emergency_contacts": List of emergency contact numbers"""


class InstructionAgent:
    @staticmethod
    def is_emergency_incident(text: str) -> bool:
        """Determines if the incident text describes an emergency or life-safety threat."""
        emergency_keywords = [
            "fire", "flames", "smoke", "burning", "catching fire", "explosion",
            "blast", "sparks flying", "gas leak", "chemical spill", "ceiling collapse",
            "building collapse", "flooding fast", "trapped", "electrocution hazard",
            "active fire", "evacuate"
        ]
        text_lower = text.lower()
        return any(k in text_lower for k in emergency_keywords)

    @staticmethod
    async def generate_safety_instructions(
        raw_description: str,
        detected_building: Optional[str] = None,
        detected_room: Optional[str] = None
    ) -> EmergencyInstructionsSchema:
        """Generates emergency safety instructions using Groq with deterministic grounding fallback."""
        b_code = detected_building or "EEC-ACAD"
        b_name = VALID_BUILDING_CODES.get(b_code, "Academic Tech Block (EEC-ACAD)")
        room_hint = detected_room or "Affected Campus Block"

        prompt_input = (
            f"Emergency Incident Description: {raw_description}\n"
            f"Building Code: {b_code} ({b_name})\n"
            f"Room / Floor: {room_hint}"
        )

        if settings.GROQ_API_KEY:
            try:
                headers = {
                    "Authorization": f"Bearer {settings.GROQ_API_KEY}",
                    "Content-Type": "application/json",
                }
                payload = {
                    "model": settings.GROQ_MODEL,
                    "messages": [
                        {"role": "system", "content": INSTRUCTION_AGENT_PROMPT},
                        {"role": "user", "content": prompt_input}
                    ],
                    "response_format": {"type": "json_object"},
                    "temperature": 0.1,
                    "max_tokens": 768,
                }
                async with httpx.AsyncClient(timeout=3.0) as client:
                    res = await client.post(settings.GROQ_API_URL, json=payload, headers=headers)
                    if res.status_code == 200:
                        content = res.json()["choices"][0]["message"]["content"]
                        parsed = json.loads(content)
                        return EmergencyInstructionsSchema(
                            is_emergency=True,
                            threat_level=parsed.get("threat_level", "CRITICAL_HAZARD"),
                            hazard_type=parsed.get("hazard_type", "FIRE"),
                            headline=parsed.get("headline") or f"🚨 CRITICAL EMERGENCY ALERT: EVACUATE {b_name.upper()}",
                            target_building=f"{b_code} - {b_name}",
                            immediate_actions=parsed.get("immediate_actions") or [],
                            evacuation_route=parsed.get("evacuation_route") or "Use exterior stairwells to exit to ground level. Do NOT use elevators.",
                            assembly_point=parsed.get("assembly_point") or SAFE_ASSEMBLY_POINTS[0],
                            emergency_contacts=parsed.get("emergency_contacts") or EMERGENCY_CONTACTS
                        )
            except Exception as e:
                logger.warning(f"Groq InstructionAgent error: {e}. Using deterministic safety fallback.")

        # Deterministic Grounded Emergency Safety Instructions
        hazard_type = "FIRE" if "fire" in raw_description.lower() or "smoke" in raw_description.lower() else "CRITICAL_HAZARD"
        headline = f"🚨 CRITICAL EMERGENCY ALERT: EVACUATE {b_name.upper()} IMMEDIATELY"

        actions = [
            "1. Cease all activities immediately. Do NOT pause to collect personal laptops or belongings.",
            "2. Alert adjacent classrooms and pull the manual fire alarm call point located near the staircase entry.",
            "3. DO NOT USE ELEVATORS under any circumstances. Proceed calmly to the nearest exterior fire staircase.",
            "4. If smoke is present, stay low to the floor where the air is cleanest; cover your nose and mouth with a cloth.",
            "5. Exit the building through ground-level exterior double doors and proceed directly to the designated assembly area.",
            "6. Once assembled at Central Ground Area A, report to your department faculty advisor for roll-call head count."
        ]

        route = f"Exit {room_hint} -> Follow emergency exit signage -> Descend via Exterior Staircase B -> Exit building to ground"
        assembly = SAFE_ASSEMBLY_POINTS[0]

        return EmergencyInstructionsSchema(
            is_emergency=True,
            threat_level="CRITICAL_HAZARD",
            hazard_type=hazard_type,
            headline=headline,
            target_building=f"{b_code} - {b_name}",
            immediate_actions=actions,
            evacuation_route=route,
            assembly_point=assembly,
            emergency_contacts=EMERGENCY_CONTACTS
        )


# ==============================================================================
# AGENT 3: MULTI-AGENT ANTI-HALLUCINATION & GROUNDING VERIFIER AGENT
# ==============================================================================

VERIFICATION_SYSTEM_PROMPT = """You are the Anti-Hallucination & Grounding Verification Agent for SRM Easwari Engineering College CampusOps.
Your mission is to audit and verify outputs from the Worker Dispatch Agent and Emergency Instruction Agent.
You must enforce strict ground truth constraints:
1. Building Grounding: Buildings MUST strictly belong to SRM Easwari campus: EEC-MAIN, EEC-ACAD, EEC-MECH-PG, EEC-ROBOTICS, EEC-AUD-FC. Reject any invented buildings, towers, or imaginary exits.
2. Safety Grounding: NEVER permit advice to use elevators during a fire/emergency. NEVER permit throwing water on electrical fires.
3. Factual Grounding: Ensure instructions strictly adhere to the user's reported problem without hallucinating casualties, fictional rooms, or unverified claims.
4. Role Grounding: Verify that tools and tasks match the technician's trade (e.g. Electrician vs Plumber).

If any hallucination or unsafe instruction is detected, correct it and output the sanitized grounded version.

Return ONLY a valid JSON object with:
- "verified": boolean (true if completely grounded, false if corrections were required)
- "hallucinations_detected": list of identified hallucinated statements or null
- "corrections_applied": list of corrective measures applied or null
- "sanitized_output": the verified, safe JSON payload."""


class AntiHallucinationAgent:
    @staticmethod
    def deterministic_verify_emergency(data: Dict[str, Any]) -> VerificationAuditResult:
        """Deterministic safety verification checks without LLM latency."""
        hallucinations: List[str] = []
        corrections: List[str] = []
        sanitized = dict(data)

        # 1. Enforce No Elevator Rule
        route = sanitized.get("evacuation_route", "")
        actions = sanitized.get("immediate_actions", [])
        if "elevator" in route.lower() and "do not" not in route.lower() and "never" not in route.lower():
            hallucinations.append("Prohibited instruction detected: Suggested using elevators during emergency.")
            sanitized["evacuation_route"] = "Proceed strictly via exterior stairwells. DO NOT use elevators."
            corrections.append("Replaced elevator suggestion with mandatory exterior staircase route.")

        for i, act in enumerate(actions):
            if "elevator" in act.lower() and "do not" not in act.lower() and "never" not in act.lower():
                hallucinations.append(f"Unsafe elevator advice in action {i+1}")
                actions[i] = "DO NOT USE ELEVATORS. Use exterior fire escape stairways only."
                corrections.append(f"Corrected action {i+1} to enforce elevator prohibition.")
        sanitized["immediate_actions"] = actions

        # 2. Enforce Safe Assembly Grounding
        assembly = sanitized.get("assembly_point", "")
        if not any(safe.split()[0] in assembly for safe in SAFE_ASSEMBLY_POINTS):
            hallucinations.append(f"Unverified assembly point '{assembly}'.")
            sanitized["assembly_point"] = SAFE_ASSEMBLY_POINTS[0]
            corrections.append(f"Grounded assembly point to '{SAFE_ASSEMBLY_POINTS[0]}'.")

        # 3. Enforce Verified Campus Contacts
        sanitized["emergency_contacts"] = EMERGENCY_CONTACTS

        is_clean = len(hallucinations) == 0
        return VerificationAuditResult(
            verified=is_clean,
            hallucinations_detected=hallucinations,
            corrections_applied=corrections,
            sanitized_output=sanitized
        )

    @staticmethod
    def deterministic_verify_dispatch(data: Dict[str, Any], worker_role: str) -> VerificationAuditResult:
        """Deterministic verification for worker dispatch email."""
        hallucinations: List[str] = []
        corrections: List[str] = []
        sanitized = dict(data)

        role_clean = worker_role.upper()
        tools = sanitized.get("tools_needed", [])
        precautions = sanitized.get("safety_precautions", [])

        # Check for electrical hazard safety rules
        if "ELEC" in role_clean:
            if any("water" in str(p).lower() and "clean with" in str(p).lower() for p in precautions):
                hallucinations.append("Dangerous advice: Water cleanup suggested for electrical hazard.")
                precautions = [p for p in precautions if "water" not in str(p).lower()]
                precautions.append("Ensure complete circuit de-energization; do not use conductive liquids near electrical panels.")
                corrections.append("Removed conductive liquid recommendation from electrical precautions.")

        sanitized["tools_needed"] = tools
        sanitized["safety_precautions"] = precautions

        is_clean = len(hallucinations) == 0
        return VerificationAuditResult(
            verified=is_clean,
            hallucinations_detected=hallucinations,
            corrections_applied=corrections,
            sanitized_output=sanitized
        )

    @staticmethod
    async def verify_and_ground_emergency(
        instructions: EmergencyInstructionsSchema
    ) -> EmergencyInstructionsSchema:
        """Audits emergency instructions through Anti-Hallucination Agent."""
        raw_dict = instructions.model_dump()

        if settings.GROQ_API_KEY:
            try:
                headers = {
                    "Authorization": f"Bearer {settings.GROQ_API_KEY}",
                    "Content-Type": "application/json",
                }
                payload = {
                    "model": settings.GROQ_MODEL,
                    "messages": [
                        {"role": "system", "content": VERIFICATION_SYSTEM_PROMPT},
                        {"role": "user", "content": f"Audit Emergency Instructions:\n{json.dumps(raw_dict)}"}
                    ],
                    "response_format": {"type": "json_object"},
                    "temperature": 0.0,
                    "max_tokens": 768,
                }
                async with httpx.AsyncClient(timeout=2.5) as client:
                    res = await client.post(settings.GROQ_API_URL, json=payload, headers=headers)
                    if res.status_code == 200:
                        parsed = json.loads(res.json()["choices"][0]["message"]["content"])
                        clean_data = parsed.get("sanitized_output") or raw_dict
                        # Also apply deterministic safety check to be 100% resilient
                        det_check = AntiHallucinationAgent.deterministic_verify_emergency(clean_data)
                        return EmergencyInstructionsSchema(**det_check.sanitized_output)
            except Exception as e:
                logger.warning(f"Groq AntiHallucinationAgent fallback: {e}")

        # Deterministic auditor
        det_check = AntiHallucinationAgent.deterministic_verify_emergency(raw_dict)
        return EmergencyInstructionsSchema(**det_check.sanitized_output)

    @staticmethod
    async def verify_and_ground_dispatch(
        dispatch: WorkerDispatchEmailSchema,
        worker_role: str
    ) -> WorkerDispatchEmailSchema:
        """Audits worker dispatch email through Anti-Hallucination Agent."""
        raw_dict = dispatch.model_dump()
        det_check = AntiHallucinationAgent.deterministic_verify_dispatch(raw_dict, worker_role)
        return WorkerDispatchEmailSchema(**det_check.sanitized_output)
