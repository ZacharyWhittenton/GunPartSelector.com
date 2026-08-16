import pulumi
import pulumi_aws as aws


def validate_account(actual_account_id: str, expected_account_id: str) -> None:
    if actual_account_id != expected_account_id:
        raise ValueError(
            f"AWS account mismatch: expected {expected_account_id}, got {actual_account_id}"
        )


def validate_hosted_zone(domain_name: str, hosted_zone_name: str) -> None:
    normalized_domain = domain_name.rstrip(".")
    normalized_zone = hosted_zone_name.rstrip(".")
    if normalized_domain != normalized_zone and not normalized_domain.endswith(
        f".{normalized_zone}"
    ):
        raise ValueError(
            f"Domain {domain_name} is not contained by Route 53 zone {hosted_zone_name}"
        )


def assert_aws_context(
    expected_account_id: str,
    domain_name: str | None,
    hosted_zone_id: str | None,
) -> None:
    identity = aws.get_caller_identity()
    try:
        validate_account(identity.account_id, expected_account_id)
    except ValueError as error:
        raise pulumi.RunError(str(error)) from error

    if domain_name is None or hosted_zone_id is None:
        return

    zone = aws.route53.get_zone(zone_id=hosted_zone_id)
    try:
        validate_hosted_zone(domain_name, zone.name)
    except ValueError as error:
        raise pulumi.RunError(str(error)) from error
