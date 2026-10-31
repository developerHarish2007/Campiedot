import json
import asyncio
import logging
from typing import Optional, List
import httpx
from app.config import settings
from app.modules.ai.schemas import IntakeExtractionSchema

logger = logging.getLogger("groq_ai_client")

EXTRACTION_SYSTEM_PROMPT = """You are the AI Incident Intelligence Assistant for SRM Easwari Engineering College CampusOps.
Your task is to analyze user chat messages and determine whether they are reporting an actual maintenance, medical/emergency, or cleaning problem, or simply chatting/greeting.

RULES:
1. GREETINGS & CHAT: If the user says "hello", "hi", "hey", "who are you", "what can you do", "thanks", "good morning", or asks a general question NOT describing an operational issue:
   - Set "is_incident": false
   - Provide a warm, helpful "assistant_reply" explaining that you are the SRM Easwari Campus Care assistant and inviting them to report any emergency, medical need, cleaning issue, broken equipment, electrical faults, or plumbing leaks.
   - Set all other fields to null/defaults.

2. REAL INCIDENTS: If the user is describing an actual campus issue or emergency:
   - Set "is_incident": true
   - Set "assistant_reply": null
   - "category": Categorize strictly into one of:
     * "SOS": Medical emergencies, fainting, unconscious student/staff, severe bleeding, injuries, seizures, heart attack, ambulance requests, immediate life-safety hazards.
     * "SWEEPER": Cleaning, dirty floors, spilled liquid, overflowing dustbin, sweeping, mopping, trash, garbage, dirty washroom, litter, food waste cleanup.
     * "ELECTRICAL": Power blackout, electrical sparks, short circuits, tripping breakers, broken switches, fans, lights, exposed wiring.
     * "PLUMBING": Water pipe burst, leaking taps, overflowing sinks, drainage clog, toilet flush failure.
     * "NETWORK": Wi-Fi down, internet disconnected, LAN cable fault, router issues.
     * "STRUCTURAL_SAFETY": Damaged furniture, cracked walls, broken doors, shattered windows, fallen ceiling tiles.
   - "extracted_room_or_node_hint": Room code (e.g. "RM-ACAD-204", "LAB-ACAD-301"), floor hint, or building name if mentioned, else null.
   - "extracted_asset_hint": Specific item mentioned (e.g. "first aid kit", "dustbin", "spill", "breaker", "switch", "tap"), else null.
   - "reporter_urgency": "P0_CRITICAL" (for all SOS medical emergencies, safety hazard, or exam disruption), "P1_HIGH", "P2_MEDIUM", or "P3_LOW". ALL SOS issues MUST have reporter_urgency "P0_CRITICAL".
   - "safety_hazard_detected": true if medical emergency, sparks, fire, smoke, flooding, or live electrical wires are mentioned, else false.
   - "concise_summary": A factual 1-sentence summary of what happened and where.

Return ONLY a valid JSON object."""


def parsed_json_urgency(val: Optional[str]) -> str:
    if val in ("P0_CRITICAL", "P1_HIGH", "P2_MEDIUM", "P3_LOW"):
        return val
    return "P2_MEDIUM"


async def _call_groq_model(client: httpx.AsyncClient, model: str, text: str, headers: dict) -> Optional[IntakeExtractionSchema]:
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
            {"role": "user", "content": f"User Message:\n{text}"}
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0.1,
        "max_tokens": 512,
    }
    response = await client.post(settings.GROQ_API_URL, json=payload, headers=headers)
    if response.status_code == 200:
        data = response.json()
        content = data["choices"][0]["message"]["content"]
        parsed = json.loads(content)
        is_incident = bool(parsed.get("is_incident", True))
        return IntakeExtractionSchema(
            is_incident=is_incident,
            assistant_reply=parsed.get("assistant_reply"),
            category=parsed.get("category"),
            extracted_room_or_node_hint=parsed.get("extracted_room_or_node_hint"),
            extracted_asset_hint=parsed.get("extracted_asset_hint"),
            reporter_urgency=parsed_json_urgency(parsed.get("reporter_urgency")),
            safety_hazard_detected=bool(parsed.get("safety_hazard_detected", False)),
            concise_summary=parsed.get("concise_summary") or text[:120],
            extractor_used=f"GROQ_{model}",
            ai_available=True,
        )
    else:
        logger.warning(f"Groq model {model} returned HTTP {response.status_code}: {response.text}")
    return None


async def extract_incident_entities(
    text: str,
    force_fallback: bool = False
) -> IntakeExtractionSchema:
    """
    Extracts entities using Groq Cloud AI model.
    If no valid API key is present or AI is unreachable, it does NOT silently create
    tickets via regex fallback; instead it informs the user to use the report form.
    """
    api_key = (settings.GROQ_API_KEY or "").strip()
    if not api_key or api_key == "your_groq_api_key_here":
        return IntakeExtractionSchema(
            is_incident=False,
            ai_available=False,
            assistant_reply="The AI assistant is currently unavailable (no active AI API key configured). Please click the 'Fill Report Form' button above to submit your issue directly.",
            concise_summary="AI unavailable; promote form submission",
            extractor_used="NO_AI_MODEL"
        )

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    # Candidate models in order of priority on Groq
    candidate_models: List[str] = []
    if settings.GROQ_MODEL and settings.GROQ_MODEL not in candidate_models:
        candidate_models.append(settings.GROQ_MODEL)
    for fallback_m in ["openai/gpt-oss-120b", "openai/gpt-oss-20b", "qwen/qwen3.8-27b"]:
        if fallback_m not in candidate_models:
            candidate_models.append(fallback_m)

    try:
        async with httpx.AsyncClient(timeout=settings.LLM_TIMEOUT_SECONDS + 2.0) as client:
            for model in candidate_models:
                try:
                    result = await asyncio.wait_for(
                        _call_groq_model(client, model, text, headers),
                        timeout=settings.LLM_TIMEOUT_SECONDS + 2.0
                    )
                    if result:
                        return result
                except (httpx.HTTPStatusError, httpx.RequestError) as e:
                    logger.warning(f"Model {model} failed: {e}")
                    continue
                except (asyncio.TimeoutError, httpx.TimeoutException):
                    logger.warning(f"Model {model} timed out")
                    continue
    except Exception as e:
        logger.warning(f"Groq API call encountered exception: {e}")

    # No AI response was possible - promote using the form instead of regex fallback
    return IntakeExtractionSchema(
        is_incident=False,
        ai_available=False,
        assistant_reply="The AI assistant could not be reached right now. Please use the 'Fill Report Form' button above to submit your maintenance report directly.",
        concise_summary="AI unreachable; promote form submission",
        extractor_used="AI_ERROR"
    )
