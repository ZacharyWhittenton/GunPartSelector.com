from pathlib import Path

import pulumi

from infrastructure.account_guard import assert_aws_context
from infrastructure.api import create_api
from infrastructure.config import InfrastructureConfig
from infrastructure.frontend import create_frontend

config = InfrastructureConfig.load()
project_config = pulumi.Config()

assert_aws_context(
    expected_account_id=config.expected_account_id,
    domain_name=config.domain_name,
    hosted_zone_id=config.hosted_zone_id,
)

if not config.lambda_archive_path.is_file():
    raise pulumi.RunError(
        f"Lambda archive not found at {config.lambda_archive_path}. "
        "Run the backend packaging script before previewing."
    )

name_prefix = f"asp-{config.environment}"
tags = {
    "Project": "Your Company Name",
    "Environment": config.environment,
    "ManagedBy": "Pulumi",
}
database_url = project_config.get_secret("databaseUrl")

api = create_api(
    name_prefix=name_prefix,
    lambda_archive_path=Path(config.lambda_archive_path),
    log_retention_days=config.log_retention_days,
    database_url=database_url,
    tags=tags,
)
frontend = create_frontend(
    name_prefix=name_prefix,
    api=api,
    domain_name=config.domain_name,
    hosted_zone_id=config.hosted_zone_id,
    certificate_arn=config.certificate_arn,
    protect_resources=config.protect_resources,
    tags=tags,
)

pulumi.export("apiEndpoint", api.endpoint)
pulumi.export("lambdaFunctionName", api.function_name)
pulumi.export("frontendBucketName", frontend.bucket_name)
pulumi.export("cloudFrontDistributionId", frontend.distribution_id)
pulumi.export("cloudFrontDomainName", frontend.distribution_domain_name)
pulumi.export("databaseProvider", config.database_provider)
