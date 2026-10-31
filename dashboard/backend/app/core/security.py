import datetime
from typing import List, Optional
from uuid import UUID
import jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

from app.config import settings
from app.core.exceptions import AuthenticationError, AuthorizationError
from app.database import get_db_pool

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")
security_scheme = HTTPBearer(auto_error=False)


class CurrentUser(BaseModel):
    id: UUID
    email: str
    full_name: str
    role: str
    department_id: Optional[UUID] = None
    base_building_code: Optional[str] = None


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict, expires_delta: Optional[datetime.timedelta] = None) -> str:
    to_encode = data.copy()
    now = datetime.datetime.now(datetime.timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + datetime.timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "iat": now})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security_scheme),
) -> CurrentUser:
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = credentials.credentials
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id_str: str = payload.get("sub")
        if not user_id_str:
            raise AuthenticationError("Token payload missing subject identifier")
        user_id = UUID(user_id_str)
    except jwt.PyJWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid or expired authentication token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Fetch user from database to ensure existence and live role
    pool = get_db_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT id, email, full_name, role, department_id, base_building_code
            FROM users
            WHERE id = $1;
            """,
            user_id,
        )
        if not row:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found in system",
            )
        return CurrentUser(
            id=row["id"],
            email=row["email"],
            full_name=row["full_name"],
            role=row["role"],
            department_id=row["department_id"],
            base_building_code=row["base_building_code"],
        )


def require_roles(allowed_roles: List[str]):
    async def role_checker(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Action requires one of the following roles: {allowed_roles}. Current role: {current_user.role}",
            )
        return current_user

    return role_checker

