from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field


class InboundIntakeRequest(BaseModel):
    text: str = Field(..., min_length=1)
    conversation_thread_id: Optional[str] = None
    idempotency_key: Optional[str] = None
    channel: str = Field(default="PORTAL_FORM")  # PORTAL_FORM, CHAT, SIMULATED_EMAIL_WEBHOOK


class ClarificationReplyRequest(BaseModel):
    reply_text: str = Field(..., min_length=1)


class EmailWebhookRequest(BaseModel):
    event_id: str
    sender: str
    subject: str
    body: str
    received_at: Optional[str] = None


class IntakeResponse(BaseModel):
    work_order_id: Optional[UUID] = None
    ticket_number: Optional[int] = None
    conversation_thread_id: Optional[str] = None
    state: str = "CONVERSATIONAL"
    is_incident: bool = True
    assistant_reply: Optional[str] = None
    requires_form: bool = False
    category: Optional[str] = None
    target_node_code: Optional[str] = None
    target_node_name: Optional[str] = None
    clarification_needed: bool = False
    clarification_question: Optional[str] = None
    partial_slots: Dict[str, Any] = Field(default_factory=dict)
    correlation_action: str = "NONE"
    concise_summary: str = ""
    extractor_used: str = "GROQ_MODEL"
    emergency_instructions: Optional[Dict[str, Any]] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
