# Site Template

A starter monorepo for new WD Web Solutions client sites — Angular frontend,
FastAPI backend (Lambda-ready via Mangum), Pulumi infrastructure, and
PostgreSQL migrations, all in one repo so the public site, API, data assets,
and cloud infrastructure can evolve independently.

This is a **template**, not a live project. All business-specific content
(name, contact info, imagery, domain) has been replaced with placeholders —
see [Using this template](#using-this-template) below before you launch a
real site from it.

## Repository layout

- `frontend/` — Angular public website
- `backend/` — FastAPI application, Lambda adapter, and pytest suite
- `data/` — provider-neutral PostgreSQL migrations and seed guidance
- `infra/` — config-driven Pulumi AWS infrastructure and safety tests
- `docs/` — browser-loadable architecture plans and decisions
- `scripts/` — cross-project packaging automation

Review the [architecture plan](docs/architecture/index.html) before changing
service boundaries or selecting the hosted PostgreSQL provider.

## Prerequisites

- Node.js 24.18 LTS (`nvm use`)
- Python 3.14 and [uv](https://docs.astral.sh/uv/)
- Pulumi CLI for infrastructure work

## Setup

```bash
python3 scripts/project.py setup
```

## Local development

Run the backend and frontend in separate terminals:

```bash
python3 scripts/project.py backend-dev
python3 scripts/project.py frontend-dev
```

The Angular site is available at <http://localhost:4200> and proxies `/api` to
FastAPI at <http://localhost:8000>.

## Verification

```bash
python3 scripts/project.py test
python3 scripts/project.py build
```

The Makefile provides shorter aliases when Make is available. The Python task
runner works without Xcode command-line tools. The build command produces the
Angular distribution and an AWS Lambda arm64 zip; it does not deploy anything.

## Deployment safety

Pulumi is operator-driven and is not part of application CI/CD. Before any
preview or deployment, configure and verify the expected AWS account ID, Route
53 hosted zone, domain, and us-east-1 ACM certificate. No database resource is
provisioned until the provider decision is approved.

## Using this template

Search-and-replace these placeholders across the repo before treating it as a
real project:

| Placeholder | Where | Replace with |
| --- | --- | --- |
| `Your Company Name` | frontend copy, `backend/pyproject.toml`, `infra/__main__.py` | Real business name |
| `Your Site Name` | `frontend/src/index.html`, `frontend/README.md` | Real site title |
| `Your Tagline Here` | `home.component.html` hero | Real tagline |
| `example.com` | footer/contact copy, `infra/Pulumi.dev.example.yaml`, `infra/tests` | Real domain |
| `hello@example.com` | footer/contact copy | Real contact email |
| `123 Main Street` / `Your City, ST 00000` | footer/contact copy | Real business address |
| `your service area` / `Your City, State` | marketing copy | Real service area |
| `site-api`, `site-infra` | `backend/pyproject.toml`, `infra/Pulumi.yaml`, package dir `backend/src/site_api` | Project-specific package names |
| `@site-template/frontend` | `frontend/package.json`, `frontend/angular.json` | Real npm/project name |
| Placeholder SVGs in `frontend/public/assets/images/**`, and the missing hero video source in `hero-video.component.html` | — | Real logo, photos, and hero video |

After renaming the Python packages, regenerate lockfiles (`uv sync` in
`backend/` and `infra/`) so `uv.lock` picks up the new project name.
