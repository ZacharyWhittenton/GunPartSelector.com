import pytest

from infrastructure.account_guard import validate_account, validate_hosted_zone


def test_accepts_expected_aws_account() -> None:
    validate_account("123456789012", "123456789012")


def test_rejects_unexpected_aws_account() -> None:
    with pytest.raises(ValueError, match="AWS account mismatch"):
        validate_account("999999999999", "123456789012")


@pytest.mark.parametrize(
    ("domain_name", "zone_name"),
    [
        ("example.com", "example.com."),
        ("www.example.com", "example.com."),
    ],
)
def test_accepts_domain_in_hosted_zone(domain_name: str, zone_name: str) -> None:
    validate_hosted_zone(domain_name, zone_name)


def test_rejects_domain_outside_hosted_zone() -> None:
    with pytest.raises(ValueError, match="is not contained"):
        validate_hosted_zone("example.com", "example.org.")
