from uuid import UUID
from fastapi import APIRouter, Depends, status, HTTPException
from app.core.security import get_current_user, CurrentUser
from app.database import acquire_db_connection
from app.modules.intake.schemas import (
    InboundIntakeRequest,
    ClarificationReplyRequest,
    EmailWebhookRequest,
    IntakeResponse,
)
from app.modules.intake.service import IntakeService

router = APIRouter(prefix="", tags=["Incident Intake & Clarification"])


@router.post("/intake", response_model=IntakeResponse, status_code=status.HTTP_201_CREATED)
async def submit_intake(
    request: InboundIntakeRequest,
    current_user: CurrentUser = Depends(get_current_user),
):
    async with acquire_db_connection(
        actor_id=current_user.id,
        actor_role=current_user.role,
        dept_id=current_user.department_id,
    ) as conn:
        async with conn.transaction():
            return await IntakeService.process_intake(
                conn,
                request=request,
                reporter_id=current_user.id,
                actor_role=current_user.role,
            )


@router.post("/intake/chat", response_model=IntakeResponse)
async def chat_intake(
    request: InboundIntakeRequest,
    current_user: CurrentUser = Depends(get_current_user),
):
    request.channel = "CHAT"
    async with acquire_db_connection(
        actor_id=current_user.id,
        actor_role=current_user.role,
        dept_id=current_user.department_id,
    ) as conn:
        async with conn.transaction():
            return await IntakeService.process_intake(
                conn,
                request=request,
                reporter_id=current_user.id,
                actor_role=current_user.role,
            )


@router.post("/intake/{thread_id}/clarify", response_model=IntakeResponse)
@router.post("/intake/clarify/{thread_id}", response_model=IntakeResponse)
async def submit_clarification_reply(
    thread_id: str,
    request: ClarificationReplyRequest,
    current_user: CurrentUser = Depends(get_current_user),
):
    async with acquire_db_connection(
        actor_id=current_user.id,
        actor_role=current_user.role,
        dept_id=current_user.department_id,
    ) as conn:
        async with conn.transaction():
            return await IntakeService.submit_clarification_reply(
                conn,
                conversation_thread_id=thread_id,
                reply_text=request.reply_text,
                reporter_id=current_user.id,
            )


@router.post("/integrations/email/webhook", response_model=IntakeResponse, status_code=status.HTTP_201_CREATED)
async def inbound_email_webhook(request: EmailWebhookRequest):
    """
    Simulated external email webhook.
    Extracts sender, subject, body, claims idempotency key based on event_id,
    and runs the intake pipeline.
    """
    async with acquire_db_connection() as conn:
        # Find or map user by email, or default to student/faculty
        user = await conn.fetchrow("SELECT id, role, department_id FROM users WHERE email = $1;", request.sender)
        if not user:
            # Map to student_1 if external sender
            user = await conn.fetchrow("SELECT id, role, department_id FROM users WHERE role = 'STUDENT_FACULTY' LIMIT 1;")

        combined_text = f"Subject: {request.subject}\nBody: {request.body}"
        intake_req = InboundIntakeRequest(
            text=combined_text,
            conversation_thread_id=f"email-{request.event_id}",
            idempotency_key=f"EMAIL-WEBHOOK-{request.event_id}",
            channel="SIMULATED_EMAIL_WEBHOOK"
        )

        async with conn.transaction():
            return await IntakeService.process_intake(
                conn,
                request=intake_req,
                reporter_id=user["id"],
                actor_role=user["role"],
            )

