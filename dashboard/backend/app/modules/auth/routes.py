from uuid import UUID
from typing import Optional
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from app.database import acquire_db_connection
from app.core.security import create_access_token

router = APIRouter(prefix="/auth", tags=["Authentication"])


class LoginRequest(BaseModel):
    email: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: UUID
    email: str
    role: str
    full_name: str


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest):
    async with acquire_db_connection() as conn:
        user = await conn.fetchrow(
            """
            SELECT id, email, full_name, role, department_id
            FROM users
            WHERE email = $1;
            """,
            request.email
        )
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"User with email '{request.email}' not found."
            )

        token = create_access_token(
            data={
                "sub": str(user["id"]),
                "role": user["role"],
                "email": user["email"]
            }
        )

        return TokenResponse(
            access_token=token,
            user_id=user["id"],
            email=user["email"],
            role=user["role"],
            full_name=user["full_name"]
        )

