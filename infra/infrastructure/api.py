import json
from dataclasses import dataclass
from pathlib import Path

import pulumi
import pulumi_aws as aws


@dataclass(frozen=True)
class ApiOutputs:
    endpoint: pulumi.Output[str]
    origin_domain_name: pulumi.Output[str]
    function_name: pulumi.Output[str]


def create_api(
    name_prefix: str,
    lambda_archive_path: Path,
    log_retention_days: int,
    database_url: pulumi.Output[str] | None,
    tags: dict[str, str],
) -> ApiOutputs:
    role = aws.iam.Role(
        f"{name_prefix}-lambda-role",
        assume_role_policy=aws.iam.get_policy_document_output(
            statements=[
                aws.iam.GetPolicyDocumentStatementArgs(
                    actions=["sts:AssumeRole"],
                    effect="Allow",
                    principals=[
                        aws.iam.GetPolicyDocumentStatementPrincipalArgs(
                            type="Service",
                            identifiers=["lambda.amazonaws.com"],
                        )
                    ],
                )
            ]
        ).json,
        tags=tags,
    )
    aws.iam.RolePolicyAttachment(
        f"{name_prefix}-lambda-basic-execution",
        role=role.name,
        policy_arn="arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole",
    )

    function_name = f"{name_prefix}-api"
    log_group = aws.cloudwatch.LogGroup(
        f"{name_prefix}-lambda-logs",
        name=f"/aws/lambda/{function_name}",
        retention_in_days=log_retention_days,
        tags=tags,
    )

    environment_variables: dict[str, pulumi.Input[str]] = {
        "APP_ENVIRONMENT": "production",
        "APP_LOG_LEVEL": "INFO",
        "APP_CORS_ORIGINS": "[]",
    }
    if database_url is not None:
        environment_variables["APP_DATABASE_URL"] = database_url

    function = aws.lambda_.Function(
        f"{name_prefix}-api",
        name=function_name,
        runtime="python3.14",
        architectures=["arm64"],
        handler="site_api.lambda_handler.handler",
        role=role.arn,
        code=pulumi.FileArchive(str(lambda_archive_path)),
        memory_size=512,
        timeout=30,
        environment=aws.lambda_.FunctionEnvironmentArgs(variables=environment_variables),
        tags=tags,
        opts=pulumi.ResourceOptions(depends_on=[log_group]),
    )

    api = aws.apigatewayv2.Api(
        f"{name_prefix}-http-api",
        name=f"{name_prefix}-http-api",
        protocol_type="HTTP",
        tags=tags,
    )
    integration = aws.apigatewayv2.Integration(
        f"{name_prefix}-lambda-integration",
        api_id=api.id,
        integration_type="AWS_PROXY",
        integration_uri=function.arn,
        integration_method="POST",
        payload_format_version="2.0",
    )
    aws.apigatewayv2.Route(
        f"{name_prefix}-default-route",
        api_id=api.id,
        route_key="$default",
        target=integration.id.apply(lambda integration_id: f"integrations/{integration_id}"),
    )

    access_log_group = aws.cloudwatch.LogGroup(
        f"{name_prefix}-api-access-logs",
        retention_in_days=log_retention_days,
        tags=tags,
    )
    aws.apigatewayv2.Stage(
        f"{name_prefix}-default-stage",
        api_id=api.id,
        name="$default",
        auto_deploy=True,
        access_log_settings=aws.apigatewayv2.StageAccessLogSettingsArgs(
            destination_arn=access_log_group.arn,
            format=json.dumps(
                {
                    "requestId": "$context.requestId",
                    "routeKey": "$context.routeKey",
                    "status": "$context.status",
                    "responseLatency": "$context.responseLatency",
                }
            ),
        ),
        tags=tags,
    )
    aws.lambda_.Permission(
        f"{name_prefix}-api-gateway-permission",
        action="lambda:InvokeFunction",
        function=function.name,
        principal="apigateway.amazonaws.com",
        source_arn=api.execution_arn.apply(lambda arn: f"{arn}/*/*"),
    )

    return ApiOutputs(
        endpoint=api.api_endpoint,
        origin_domain_name=api.api_endpoint.apply(
            lambda endpoint: endpoint.removeprefix("https://")
        ),
        function_name=function.name,
    )
