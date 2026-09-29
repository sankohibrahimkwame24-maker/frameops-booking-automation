from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "FrameOps Booking Automation"
    environment: str = "development"
    database_url: str = "sqlite:///./frameops_bookings.db"
    calendly_api_token: str = ""
    calendly_webhook_signing_key: str = ""
    signature_tolerance_seconds: int = 180
    resend_api_key: str = ""
    email_from: str = ""
    owner_email: str = ""
    admin_username: str = "admin"
    admin_password: str = ""
    max_body_bytes: int = 1_000_000
    store_raw_payload: bool = False
    outbox_max_attempts: int = 5

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    def validate_production(self) -> None:
        required = {
            "DATABASE_URL": self.database_url,
            "CALENDLY_API_TOKEN": self.calendly_api_token,
            "CALENDLY_WEBHOOK_SIGNING_KEY": self.calendly_webhook_signing_key,
            "RESEND_API_KEY": self.resend_api_key,
            "EMAIL_FROM": self.email_from,
            "OWNER_EMAIL": self.owner_email,
            "ADMIN_PASSWORD": self.admin_password,
        }
        missing = [name for name, value in required.items() if not value]
        if missing:
            raise RuntimeError(
                "Missing required production environment variables: " + ", ".join(missing)
            )
        if len(self.admin_password) < 12:
            raise RuntimeError("ADMIN_PASSWORD must be at least 12 characters in production.")


@lru_cache
def get_settings() -> Settings:
    return Settings()
