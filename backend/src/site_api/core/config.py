from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

INSECURE_DEFAULT_JWT_SECRET_KEY = "insecure-local-development-secret"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="APP_",
        extra="ignore",
    )

    app_name: str = "Site API"
    api_prefix: str = "/api"
    environment: Literal["local", "test", "production"] = "local"
    log_level: str = "INFO"
    database_url: str | None = None
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:4200"])
    jwt_secret_key: str = INSECURE_DEFAULT_JWT_SECRET_KEY
    jwt_algorithm: str = "HS256"
    jwt_access_token_expires_minutes: int = 60
    blog_uploads_dir: str = "uploads/blog"
    anthropic_api_key: str | None = None
    chat_model: str = "claude-opus-5"
    stripe_secret_key: str | None = None
    stripe_webhook_secret: str | None = None
    marketplace_currency: str = "usd"
    marketplace_uploads_dir: str = "uploads/marketplace"
    public_site_url: str = "http://localhost:4200"
    aws_ses_region: str = "us-east-1"
    email_sender_address: str | None = None
    admin_notification_email: str | None = None

    @model_validator(mode="after")
    def _require_real_jwt_secret_in_production(self) -> Settings:
        if (
            self.environment == "production"
            and self.jwt_secret_key == INSECURE_DEFAULT_JWT_SECRET_KEY
        ):
            raise ValueError("APP_JWT_SECRET_KEY must be set to a real secret in production")
        return self
