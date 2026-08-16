from pathlib import Path

import pulumi
import pytest

from infrastructure.config import InfrastructureConfig


def make_config(**overrides: object) -> InfrastructureConfig:
    values: dict[str, object] = {
        "environment": "dev",
        "expected_account_id": "123456789012",
        "domain_name": None,
        "hosted_zone_id": None,
        "certificate_arn": None,
        "lambda_archive_path": Path("../backend/dist/lambda.zip"),
        "database_provider": "deferred",
        "protect_resources": True,
        "log_retention_days": 30,
    }
    values.update(overrides)
    return InfrastructureConfig(**values)  # type: ignore[arg-type]


def test_accepts_default_distribution_configuration() -> None:
    make_config().validate()


def test_custom_domain_settings_must_be_complete() -> None:
    config = make_config(domain_name="example.com")

    with pytest.raises(pulumi.RunError, match="must be configured together"):
        config.validate()


def test_cloudfront_certificate_must_be_in_us_east_1() -> None:
    config = make_config(
        domain_name="example.com",
        hosted_zone_id="Z0123456789EXAMPLE",
        certificate_arn="arn:aws:acm:us-west-2:123456789012:certificate/00000000-0000-0000-0000-000000000000",
    )

    with pytest.raises(pulumi.RunError, match="must be in us-east-1"):
        config.validate()
