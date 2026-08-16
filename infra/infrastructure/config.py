from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import pulumi

DatabaseProvider = Literal["deferred", "aurora-serverless-v2", "external-postgres"]


@dataclass(frozen=True)
class InfrastructureConfig:
    environment: str
    expected_account_id: str
    domain_name: str | None
    hosted_zone_id: str | None
    certificate_arn: str | None
    lambda_archive_path: Path
    database_provider: DatabaseProvider
    protect_resources: bool
    log_retention_days: int

    @classmethod
    def load(cls) -> InfrastructureConfig:
        config = pulumi.Config()
        infra_directory = Path(__file__).resolve().parents[1]
        archive_setting = config.get("lambdaArchivePath") or "../backend/dist/lambda.zip"
        archive_path = Path(archive_setting)
        if not archive_path.is_absolute():
            archive_path = (infra_directory / archive_path).resolve()

        database_provider = config.get("databaseProvider") or "deferred"
        if database_provider not in {
            "deferred",
            "aurora-serverless-v2",
            "external-postgres",
        }:
            raise pulumi.RunError(f"Unsupported databaseProvider: {database_provider}")

        protect_resources = config.get_bool("protectResources")

        instance = cls(
            environment=config.get("environment") or pulumi.get_stack(),
            expected_account_id=config.require("expectedAccountId"),
            domain_name=config.get("domainName"),
            hosted_zone_id=config.get("hostedZoneId"),
            certificate_arn=config.get("certificateArn"),
            lambda_archive_path=archive_path,
            database_provider=database_provider,
            protect_resources=True if protect_resources is None else protect_resources,
            log_retention_days=config.get_int("logRetentionDays") or 30,
        )
        instance.validate()
        return instance

    def validate(self) -> None:
        custom_domain_values = (
            self.domain_name,
            self.hosted_zone_id,
            self.certificate_arn,
        )
        if any(custom_domain_values) and not all(custom_domain_values):
            raise pulumi.RunError(
                "domainName, hostedZoneId, and certificateArn must be configured together"
            )
        if self.certificate_arn is not None and ":us-east-1:" not in self.certificate_arn:
            raise pulumi.RunError("CloudFront certificateArn must be in us-east-1")
        if self.database_provider != "deferred":
            pulumi.log.warn(
                "databaseProvider records the intended provider only; this stack does not yet "
                "provision database resources"
            )
