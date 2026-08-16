# Backend

FastAPI application designed for AWS Lambda behind API Gateway. Mangum adapts
API Gateway events to ASGI. PostgreSQL access is isolated behind a repository
interface so the hosted serverless provider can be selected later.

## Local setup

```bash
uv sync
cp .env.example .env
uv run uvicorn site_api.main:app --reload
```

The API is available at <http://localhost:8000/api>. The health endpoint does
not connect to PostgreSQL, so health checks do not wake a paused database.

## Tests and quality checks

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
```

All test dependencies are development-only and are not included in the Lambda
deployment package.

## Database migrations

Migrations live in `../data/migrations` and use this service's SQLAlchemy
metadata. Set `APP_DATABASE_URL`, then run:

```bash
uv run alembic upgrade head
```
