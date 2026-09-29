from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_name: str = "FrameOps Booking Automation"
    environment: str = "development"
    database_url: str = "sqlite:///./frameops_bookings.db"
    calendly_webhook_signing_key: str = ""
    calendly_api_token: str = ""
    resend_api_key: str = ""
    email_from: str = "FrameOps <onboarding@resend.dev>"
    owner_email: str = ""
    signature_tolerance_seconds: int = 180
    max_body_bytes: int = 1_000_000
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore")

@lru_cache
def get_settings() -> Settings:
    return Settings()
