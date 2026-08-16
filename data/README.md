# Data

This directory owns provider-neutral PostgreSQL assets.

- `migrations/` contains Alembic schema migrations.
- `seeds/` documents local-only seed data.

The hosted PostgreSQL provider is intentionally undecided. Application code
uses a standard SQLAlchemy PostgreSQL URL and does not depend on vendor APIs.
Production data and credentials must never be committed here.
