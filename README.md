# GReEnAI — Generic Reconciliation ENgine with AI

[![CI](https://github.com/OWNER/REPO/actions/workflows/ci.yml/badge.svg)](https://github.com/OWNER/REPO/actions/workflows/ci.yml)
[![CI Minimal](https://github.com/OWNER/REPO/actions/workflows/ci-minimal.yml/badge.svg)](https://github.com/OWNER/REPO/actions/workflows/ci-minimal.yml)
[![coverage](https://img.shields.io/badge/coverage-unknown-lightgrey.svg)](coverage.xml)

Replace OWNER/REPO in the badge URLs with your GitHub organization and repository name to enable live badges. Example: https://github.com/your-org/greenai

GReEnAI is a reconciliation engine that leverages AI to match and reconcile data from disparate sources. It provides a backend-for-frontend (BFF) API, batch processing jobs, and a web-based user interface.

Quick copy-paste commands to start the stack (dev and prod-like).

Prerequisites: Docker & Docker Compose v2+ installed.

Dev (fast feedback, hot-reload):

```bash
# Start API, DB and the frontend dev server (uses profile 'dev')
docker compose --profile dev up --build

# Run batch jobs on-demand (generate, ingest, diff, ai)
docker compose --profile jobs run --rm generate-data
docker compose --profile jobs run --rm ingest-job
docker compose --profile jobs run --rm diff-job
docker compose --profile jobs run --rm ai-job
```

Prod-like (build frontend static & serve via Nginx):

```bash
# Build and run the production-like frontend image (profile 'prod')
docker compose --profile prod up --build

# To run in background
docker compose --profile prod up --build -d

# Tear down and remove volumes
docker compose down -v
```

Environment variables

- Create a `.env` file at the repo root to override DB URLs if required. Example:

```text
# For local development ONLY (do not commit `.env` with secrets):
# For BFF (asyncpg)
DATABASE_URL=postgresql+asyncpg://postgres:${POSTGRES_PASSWORD}@db:5432/${POSTGRES_DB}

# For batch jobs (psycopg)
DB_URL=postgresql://postgres:${POSTGRES_PASSWORD}@db:5432/${POSTGRES_DB}
```

See `SystemRequirements.md` and `frontend/README.md` for more details.

Note about host mounts
----------------------

For local development we provide dev-only services that mount your host
source tree into containers for fast feedback and hot-reload. These dev
services are intentionally separate from the production services and are
activated using the `dev` profile. Examples:

- `bff-dev`: development BFF that mounts `./bff` and enables hot-reload.
- `ingest-job-dev`, `diff-job-dev`, `ai-job-dev`: development variants of
	the batch jobs that mount `./backend` for iterative development.

Do not mount host source in production deployments. The default service
names (without `-dev`) are intended for production images and will not
mount your working tree when started without the `dev` profile.

## Linting & Formatting (Developer Setup)

This project uses `black` and `ruff` to enforce consistent formatting and linting.

Install development tools:

```bash
python -m pip install -r requirements-dev.txt
```

Install the `pre-commit` hooks (runs on git commits):

```bash
pre-commit install
pre-commit run --all-files
```

Run the linters manually:

```bash
# Check formatting (Black)
black --check .

# Apply formatting (Black)
black .

# Run Ruff (linting and autofix)
ruff check .
ruff format .
```

Virtual environment (recommended)

```bash
# create venv
python3 -m venv .venv

# activate
source .venv/bin/activate

# upgrade pip
pip install --upgrade pip

# install runtime deps
pip install --only-binary=:all: -r requirements.lock.txt

# install dev deps
pip install --only-binary=:all: -r requirements-dev.txt

Use wheels-only installs
------------------------

To avoid local native builds and ensure reproducible installs, always
install from prebuilt wheels when possible. This repository expects a
consistent Python runtime (use Python 3.11) and wheel-based installs:

```bash
# Example: install runtime dependencies from consolidated lockfile
pip install --only-binary=:all: -r requirements.lock.txt

# Install dev tools (wheels-only)
pip install --only-binary=:all: -r requirements-dev.txt
```

If a package does not publish wheels for your platform/Python version,
prefer upgrading/downgrading to a version that does or run installs in
CI where build toolchains are available. Avoid building wheels locally
on developer machines to reduce friction.
```

Note: add `.venv/` to `.gitignore` to avoid committing the virtualenv.

Secrets guidance
-----------------

- Never commit secrets to source control. Use a `.env` only for local
	development and never check it into git. Use a secret manager (AWS
	Secrets Manager, HashiCorp Vault, Kubernetes Secrets) for production.
- Ensure your deployment platform injects the required `DATABASE_URL` or
	`DB_URL` environment variables; the application will fail to start if
	these variables are missing to avoid accidental usage of insecure
	defaults.

Database migrations
-------------------

This repository includes an Alembic scaffold under the `alembic/` folder.
Before deploying, generate and apply migrations against your target database.

Local example:

```bash
# Install alembic in your environment
pip install alembic

# Create a new revision (autogenerate requires models/metadata hooked into alembic/env.py)
alembic revision -m "create initial schema" --autogenerate

# Apply migrations
alembic upgrade head
```

In CI/CD ensure `DATABASE_URL` (or `DB_URL`) is set in the environment so Alembic can connect.

