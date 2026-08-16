# Infrastructure

Config-driven Pulumi for the AWS serverless platform. Pulumi is intentionally
used for initial infrastructure setup and operator-driven changes, not as an
application deployment step inside CI/CD.

## Resources

- private S3 bucket for the Angular build
- CloudFront distribution with Origin Access Control and SPA routing
- API Gateway HTTP API
- Python 3.14 Lambda running FastAPI through Mangum
- CloudWatch logs with retention
- optional Route 53 aliases and ACM certificate

The database provider is deliberately deferred. A secret `databaseUrl` setting
can connect the Lambda to any PostgreSQL-compatible provider after that decision
is made. Aurora or private-network PostgreSQL will also require a VPC component.

## Safety guard

Every stack requires `expectedAccountId`. Evaluation stops if AWS STS reports a
different account. When a custom domain is configured, the Route 53 hosted zone
is also checked against the requested domain. Never remove these checks to make
a preview pass.

## Configure a stack

```bash
uv sync
pulumi stack init dev
pulumi config set aws:region us-east-1
pulumi config set expectedAccountId 123456789012
pulumi config set domainName example.com
pulumi config set hostedZoneId Z0123456789EXAMPLE
pulumi config set certificateArn <us-east-1-certificate-arn>
pulumi config set --secret databaseUrl <postgresql-sqlalchemy-url>
```

Build `../backend/dist/lambda.zip` before previewing. Do not preview or deploy
until the account ID, hosted zone, and domain are confirmed to belong together.

## Validate locally

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
```
