import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(__file__), "..", "..", ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # Database Settings
    POSTGRES_USER: str = Field(default="postgres")
    POSTGRES_PASSWORD: str = Field(default="postgres")
    POSTGRES_DB: str = Field(default="campusops")
    POSTGRES_HOST: str = Field(default="localhost")
    POSTGRES_PORT: int = Field(default=5432)
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/campusops"
    )

    # Security & Tokens
    SECRET_KEY: str = Field(
        default="campusops_super_secret_jwt_key_2026_production_srm_easwari"
    )
    ALGORITHM: str = Field(default="HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30)
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=7)

    # Campus Settings
    CAMPUS_NAME: str = Field(default="SRM Easwari Engineering College")
    CAMPUS_CODE: str = Field(default="EEC")
    CAMPUS_LAT: float = Field(default=13.0324)
    CAMPUS_LON: float = Field(default=80.1810)

    # AI & Groq Configuration
    GROQ_API_KEY: str = Field(default="")
    GROQ_MODEL: str = Field(default="llama-3.3-70b-versatile")
    GROQ_API_URL: str = Field(default="https://api.groq.com/openai/v1/chat/completions")
    LLM_TIMEOUT_SECONDS: float = Field(default=2.5)
    LLM_FALLBACK_MODE: str = Field(default="DETERMINISTIC_REGEX")

    # Resend Email Integration
    RESEND_API_KEY: str = Field(default="")
    RESEND_API_URL: str = Field(default="https://api.resend.com/emails")
    RESEND_FROM_EMAIL: str = Field(default="CampusOps Alerts <onboarding@resend.dev>")

    # Server Settings
    BACKEND_HOST: str = Field(default="0.0.0.0")
    BACKEND_PORT: int = Field(default=8000)
    OUTBOX_WORKER_POLL_INTERVAL: int = Field(default=3)


settings = Settings()

