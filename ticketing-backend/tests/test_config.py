import pytest
from pydantic import ValidationError

from app.core.config import Settings


def valid_staging_settings() -> dict[str, object]:
    return {
        "app_env": "staging",
        "secret_key": "a-secure-staging-secret-key-with-32-characters",
        "validation_station_cookie_secure": True,
        "database_url": "postgresql://ticketing:ticketing@postgres:5432/ticketing",
        "redis_url": "redis://redis:6379/0",
        "rate_limit_enabled": True,
        "smtp_host": "smtp.example.invalid",
        "smtp_username": "smtp-user",
        "smtp_password": "smtp-password",
        "smtp_from_email": "sender@example.invalid",
        "frontend_base_url": "https://staging.example.invalid",
        "backend_base_url": "https://staging.example.invalid/api",
        "object_storage_backend": "s3",
        "s3_endpoint_url": "http://minio:9000",
        "s3_access_key": "staging-access-key",
        "s3_secret_key": "staging-secret-key",
        "s3_bucket": "ticketing-media",
    }


def test_valid_staging_configuration_is_accepted():
    settings = Settings(**valid_staging_settings())

    assert settings.app_env == "staging"
    assert settings.api_docs_enabled is False
    assert settings.trusted_proxy_headers_enabled is True


def test_api_documentation_is_available_in_local_and_test_environments():
    values = valid_staging_settings()
    values["app_env"] = "development"

    settings = Settings(**values)

    assert settings.api_docs_enabled is True
    assert settings.trusted_proxy_headers_enabled is False

    values["app_env"] = "test"
    settings = Settings(**values)

    assert settings.api_docs_enabled is True


def test_staging_configuration_rejects_placeholders():
    values = valid_staging_settings()
    values["s3_secret_key"] = "replace_me"

    with pytest.raises(ValidationError, match="S3 configuration contains placeholder values"):
        Settings(**values)


def test_staging_configuration_rejects_demo_data():
    values = valid_staging_settings()
    values["demo_data_enabled"] = True

    with pytest.raises(ValidationError, match="DEMO_DATA_ENABLED must be false"):
        Settings(**values)


def test_superadmin_email_must_be_deliverable():
    values = valid_staging_settings()
    values["superadmin_email"] = "admin@example.invalid"

    with pytest.raises(ValidationError, match="valid email address"):
        Settings(**values)
