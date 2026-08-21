# GunPartSelector.com

An AR-15 build configurator and affiliate parts catalog: browse parts by
category, drop them onto an interactive 3D model, get live compatibility
checks (caliber, buffer tube, handguard interface, gas system, receiver
platform), and share the finished build with a link. "Add to Build" and
product links send the visitor to a retailer to complete the purchase —
this site doesn't hold inventory or ship parts itself. There's also a small
merch store (apparel) with its own checkout.

Angular frontend, FastAPI backend (Lambda-ready via Mangum), PostgreSQL via
Alembic migrations, Pulumi infrastructure.

## Repository layout

- `frontend/` — Angular site: the build configurator, parts catalog, merch
  store, blog, and admin
- `backend/` — FastAPI application, Lambda adapter, and pytest suite
- `data/` — PostgreSQL migrations and seed/import scripts
- `infra/` — config-driven Pulumi AWS infrastructure and safety tests
- `docs/` — browser-loadable architecture plans and decisions
- `scripts/` — cross-project task runner (`project.py`)

## Prerequisites

- Node.js 24.18 LTS (`nvm use` — see [Local development](#local-development)
  below if `ng serve` complains about your Node version)
- Python 3.14 and [uv](https://docs.astral.sh/uv/)
- PostgreSQL running locally (or reachable via `APP_DATABASE_URL`)
- Pulumi CLI, only if you're touching infrastructure

## Setup

```bash
python3 scripts/project.py setup
```

## Local development

Run the backend and frontend in **two separate terminals**, both from the
repository root:

```bash
python3 scripts/project.py backend-dev
```

```bash
python3 scripts/project.py frontend-dev
```

The Angular site is available at <http://localhost:4200> and proxies `/api`
to FastAPI at <http://localhost:8000>.

### "The Angular CLI requires a minimum Node.js version..."

This means the terminal you ran `frontend-dev` in is using your system's
default Node instead of the version this project needs. Fix it in that same
terminal, then re-run the command:

```bash
nvm use
```

(`nvm use` with no version reads `.nvmrc` at the repo root and switches to
24.18.0 automatically.) If you get "N/A: version not found", install it
first with `nvm install`.

### "nvm: command not found"

Your terminal window is running bash instead of your Mac's default zsh, so
it never loaded `~/.zshrc` (where nvm gets set up). Switch the window to
zsh, then retry:

```bash
zsh
```

```bash
nvm use
```

Opening a brand new Terminal window/tab instead of reusing an old one
usually avoids this.

## Database

Apply migrations and load sample catalog data from `backend/`:

```bash
uv run alembic upgrade head
uv run python ../data/seeds/seed_catalog_data.py
```

## Verification

```bash
python3 scripts/project.py test
python3 scripts/project.py build
```

The build command produces the Angular distribution and an AWS Lambda
arm64 zip; it does not deploy anything.

## Deployment safety

Pulumi is operator-driven and is not part of application CI/CD. Before any
preview or deployment, confirm the target AWS account ID, Route 53 hosted
zone, domain, and us-east-1 ACM certificate.
