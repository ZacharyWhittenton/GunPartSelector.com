import pytest
from pydantic import ValidationError

from site_api.core.config import Settings


def test_production_rejects_default_jwt_secret() -> None:
    with pytest.raises(ValidationError):
        Settings(environment="production", database_url="postgresql+psycopg://x/y")


def test_production_accepts_real_jwt_secret() -> None:
    settings = Settings(
        environment="production",
        database_url="postgresql+psycopg://x/y",
        jwt_secret_key="a-real-production-secret",
    )

    assert settings.jwt_secret_key == "a-real-production-secret"
