import re
from typing import Optional, Tuple
from app.modules.ai.schemas import IntakeExtractionSchema


def extract_deterministic_fallback(text: str) -> IntakeExtractionSchema:
    """
    High-speed deterministic regex and keyword fallback parser.
    Executes in < 1ms with zero external network dependencies.
    """
    text_lower = text.lower()

    # 1. Exact node / room code regex pattern
    node_pattern = r"\b(RM-[A-Z0-9-]+|LAB-[A-Z0-9-]+|EEC-[A-Z0-9-]+|SUBSTATION-[A-Z0-9-]+|PANEL-[A-Z0-9-]+|SW-[A-Z0-9-]+|AHU-[A-Z0-9-]+)\b"
    node_match = re.search(node_pattern, text, re.IGNORECASE)
    room_hint: Optional[str] = None
    if node_match:
        room_hint = node_match.group(1).upper()
    else:
        # Check floor hints: e.g. "3rd floor lab", "2nd floor classroom"
        floor_match = re.search(r"\b(1st|2nd|3rd|4th|5th|ground)\s+floor(?:\s+([a-zA-Z0-9_-]+))?\b", text, re.IGNORECASE)
        if floor_match:
            room_hint = floor_match.group(0).strip()
        else:
            # Check building hints
            bldg_match = re.search(r"\b(Main\s+Admin|Admin|Academic|Mechanical|Robotics|Auditorium|Food\s+Court)\s*(?:Block|Building)?\b", text, re.IGNORECASE)
            if bldg_match:
                room_hint = bldg_match.group(0).strip()

    # 2. Asset hints
    asset_keywords = {
        "projector": ["projector", "projection", "smart board", "display"],
        "breaker": ["mccb", "mcb", "circuit breaker", "breaker", "fuse", "panel"],
        "switch": ["network switch", "poe switch", "core switch", "ethernet switch"],
        "access point": ["wi-fi router", "access point", "ap", "wifi router"],
        "air conditioner": ["ac", "air conditioner", "ahu", "split ac"],
        "pipe": ["water pipe", "drainage", "tap", "faucet", "valve"],
        "light": ["tube light", "led panel", "bulb", "lighting"],
    }
    extracted_asset = None
    for asset, keywords in asset_keywords.items():
        if any(kw in text_lower for kw in keywords):
            extracted_asset = asset
            break

    # 3. Category inference via keyword dictionaries
    category_scores = {
        "SOS": [
            "medical", "emergency", "doctor", "ambulance", "faint", "fainted", "unconscious",
            "injury", "injured", "bleed", "bleeding", "first aid", "firstaid", "heart", "chest pain",
            "breath", "breathing", "fracture", "dizzy", "asthma", "seizure", "sos", "urgent medical", "hospital",
            "collapsed", "hurt", "fell down", "accident"
        ],
        "SWEEPER": [
            "clean", "cleaning", "sweep", "sweeper", "sweeping", "mop", "mopping", "trash", "garbage",
            "dustbin", "spill", "spilled", "dirty", "litter", "muddy", "stain", "vomit", "waste",
            "debris", "housekeeping", "sanitation", "broom", "dust"
        ],
        "ELECTRICAL": ["spark", "sparking", "electrical", "blackout", "power", "breaker", "mcb", "mccb", "voltage", "wire", "shock", "tripping", "short circuit", "fan", "light", "bulb", "socket", "ac", "air conditioner"],
        "NETWORK": ["wifi", "wi-fi", "internet", "lan", "ethernet", "network", "packet loss", "ping", "router", "switch", "offline", "projector", "hdmi", "display", "screen"],
        "PLUMBING": ["pipe", "leak", "leakage", "water", "washroom", "toilet", "tap", "faucet", "drainage", "flooding", "sewage", "basin", "flush"],
        "STRUCTURAL_SAFETY": ["crack", "ceiling", "wall", "broken", "railing", "glass", "door lock", "structural", "window", "door", "bench", "table", "chair"],
    }

    matched_category = None
    max_matches = 0
    for cat, kws in category_scores.items():
        count = sum(1 for kw in kws if re.search(r"\b" + re.escape(kw) + r"\b", text_lower))
        if count > max_matches:
            max_matches = count
            matched_category = cat

    # Default category if none detected
    if not matched_category:
        if any(w in text_lower for w in ["medical", "faint", "bleed", "injur", "emergency", "sos", "doctor", "ambulance"]):
            matched_category = "SOS"
        elif any(w in text_lower for w in ["clean", "sweep", "trash", "dustbin", "spill", "dirty", "garbage", "mop"]):
            matched_category = "SWEEPER"
        elif "wifi" in text_lower or "internet" in text_lower or "network" in text_lower:
            matched_category = "NETWORK"
        elif "water" in text_lower or "leak" in text_lower:
            matched_category = "PLUMBING"
        elif "light" in text_lower or "power" in text_lower:
            matched_category = "ELECTRICAL"
        else:
            matched_category = "ELECTRICAL"

    if matched_category == "SOS":
        safety_hazard = True
        urgency = "P0_CRITICAL"

    # 4. Safety Hazard Detection
    hazard_keywords = ["spark", "sparking", "fire", "smoke", "burning smell", "live wire", "shock", "flooding", "collapse", "explosion"]
    safety_hazard = any(hk in text_lower for hk in hazard_keywords)

    # 5. Urgency Calculation
    has_exam = "exam" in text_lower or "examination" in text_lower or "test" in text_lower
    if safety_hazard:
        urgency = "P0_CRITICAL"
    elif has_exam:
        urgency = "P0_CRITICAL" if max_matches > 0 else "P1_HIGH"
    elif "urgent" in text_lower or "immediately" in text_lower or "emergency" in text_lower or "critical" in text_lower:
        urgency = "P1_HIGH"
    else:
        urgency = "P2_MEDIUM"

    # 6. Concise Summary
    summary = text.strip()
    if len(summary) > 120:
        summary = summary[:117] + "..."

    return IntakeExtractionSchema(
        category=matched_category,
        extracted_room_or_node_hint=room_hint,
        extracted_asset_hint=extracted_asset,
        reporter_urgency=urgency,
        safety_hazard_detected=safety_hazard,
        concise_summary=summary,
        extractor_used="DETERMINISTIC_REGEX_FALLBACK"
    )

