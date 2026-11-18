from pathlib import Path
from typing import Literal

from pydantic import EmailStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_DIR = Path(__file__).resolve().parents[2]
BASE_DIR = BACKEND_DIR.parent  # Repository root locally, / inside the container


class Settings(BaseSettings):
    app_env: str = "development"
    app_name: str = "Ticketing Demo API"
    log_level: str = "INFO"
    demo_data_enabled: bool = False
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24 * 7
    password_reset_token_expire_minutes: int = 30
    guest_checkout_access_expire_minutes: int = 60 * 24
    validation_station_activation_expire_minutes: int = 60 * 24 * 7
    validation_station_session_expire_minutes: int = 60 * 24 * 2
    validation_station_cookie_secure: bool = False

    database_url: str
    redis_url: str | None = None
    rate_limit_enabled: bool = False
    rate_limit_key_prefix: str = "ticketing:rate-limit"

    smtp_host: str
    smtp_port: int = 587
    smtp_username: str
    smtp_password: str
    smtp_from_email: str
    smtp_from_name: str = "Ticketing Demo"
    smtp_use_tls: bool = True
    smtp_timeout_seconds: float = 10.0
    email_delivery_enabled: bool = True
    organizer_contact_email: str | None = None

    frontend_base_url: str = "http://localhost:5173"
    backend_base_url: str = "http://localhost:8000"
    upload_dir: str = str(BACKEND_DIR / "uploads")
    event_image_max_bytes: int = 8 * 1024 * 1024
    object_storage_backend: Literal["local", "s3"] = "local"
    s3_endpoint_url: str | None = None
    s3_access_key: str | None = None
    s3_secret_key: str | None = None
    s3_bucket: str = "ticketing-media"
    s3_region: str = "us-east-1"
    s3_use_ssl: bool = False
    cors_allow_origins: str = (
        "http://localhost:5173,"
        "http://127.0.0.1:5173,"
        "http://localhost:5174,"
        "http://127.0.0.1:5174"
    )

    superadmin_email: EmailStr | None = None
    superadmin_password: str | None = None
    superadmin_full_name: str | None = None

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        extra="ignore",
    )

    @property
    def api_docs_enabled(self) -> bool:
        return self.app_env.lower() in {"development", "dev", "local", "test"}

    @property
    def trusted_proxy_headers_enabled(self) -> bool:
        return self.app_env.lower() in {"staging", "production"}

    @model_validator(mode="after")
    def validate_deployment_security(self):
        if self.app_env.lower() not in {"staging", "production"}:
            return self

        if self.demo_data_enabled:
            raise ValueError("DEMO_DATA_ENABLED must be false outside local development")

        def is_placeholder(value: str | None) -> bool:
            return not value or "replace" in value.lower()

        if len(self.secret_key) < 32 or is_placeholder(self.secret_key):
            raise ValueError("SECRET_KEY must be a non-placeholder value of at least 32 characters")
        if not self.validation_station_cookie_secure:
            raise ValueError("VALIDATION_STATION_COOKIE_SECURE must be true")
        if not self.frontend_base_url.startswith("https://") or is_placeholder(self.frontend_base_url):
            raise ValueError("FRONTEND_BASE_URL must use HTTPS")
        if not self.backend_base_url.startswith("https://") or is_placeholder(self.backend_base_url):
            raise ValueError("BACKEND_BASE_URL must use HTTPS")
        if self.rate_limit_enabled and not self.redis_url:
            raise ValueError("REDIS_URL is required when rate limiting is enabled")
        if self.object_storage_backend == "s3" and not all(
            [self.s3_endpoint_url, self.s3_access_key, self.s3_secret_key, self.s3_bucket]
        ):
            raise ValueError("S3 configuration is incomplete")
        if self.object_storage_backend == "s3" and any(
            is_placeholder(value)
            for value in [self.s3_access_key, self.s3_secret_key, self.s3_bucket]
        ):
            raise ValueError("S3 configuration contains placeholder values")
        if self.email_delivery_enabled and any(
            is_placeholder(value)
            for value in [
                self.smtp_host,
                self.smtp_username,
                self.smtp_password,
                self.smtp_from_email,
            ]
        ):
            raise ValueError("SMTP configuration contains placeholder values")
        if self.superadmin_email and is_placeholder(self.superadmin_email):
            raise ValueError("SUPERADMIN_EMAIL contains a placeholder value")
        if self.superadmin_password and is_placeholder(self.superadmin_password):
            raise ValueError("SUPERADMIN_PASSWORD contains a placeholder value")
        return self


settings = Settings()
