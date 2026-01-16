# Developer Setup (Python 3.11)

This file documents the reproducible local developer environment used for CI and the staging harness.

## Prerequisites

- macOS (or Linux) with `python3.11` installed and on PATH
- `docker` and `docker-compose` (for the staging harness)
- Optional: `k6` locally if you prefer running load tests outside Docker

## Create the Python 3.11 virtualenv

```bash
# from repo root
python3.11 -m venv .venv_py311
source .venv_py311/bin/activate
python -m pip install --upgrade pip
# install runtime deps
pip install -r requirements.txt
# install dev deps (linters, mypy, pytest, pip-audit, etc.)
pip install -r requirements-dev.txt
```

If you use a lockfile workflow, prefer installing from the lockfile that matches CI.

Optional: strict lockfile workflow with pip-tools

If you want strict, reproducible installs where the environment exactly matches a compiled lockfile, consider using `pip-tools` and `pip-sync`. Example:

```bash
# generate a lockfile locally (if you maintain .in files):
# pip-compile requirements.in --output-file=requirements.lock.txt --generate-hashes

# install pip-tools and sync exactly to the lockfile
pip install pip-tools
pip-sync requirements.lock.txt
```

Note: `pip-sync` will remove packages not present in the lockfile; use with care in developer machines and prefer CI for enforced sync.

## Run linters and tests (recommended)

```bash
# inside .venv_py311
./scripts/run_linters.sh
pytest -q --maxfail=1 --cov=./ --cov-report=xml:coverage.xml
# optionally run security checks
pip-audit -r requirements.lock.txt || pip-audit
```

`./scripts/run_linters.sh` runs `mypy`, `ruff`, and `black --check` in this repository.

Local lockfile check

```bash
# Quick local check that your `requirements.lock.txt` is up-to-date with `requirements.in`:
./scripts/check_lockfile.sh
```

## Reproduce staging harness (end-to-end, local Docker)

Requirements: Docker daemon running and enough resources.

```bash
# pull required images (optional but helpful)
docker pull postgres:15
docker pull redis:7
# run the staging harness (creates a Docker network, starts DB/Redis, applies schema, builds BFF image, runs k6)
bash ./scripts/run_staging_load.sh
```

Notes:
- The staging script preprocesses `database/schema/*.sql` to remove markdown fences and creates required Postgres extensions before applying the schema.
- The script builds the BFF image using the `bff/Dockerfile` (Python 3.11) and runs the container on the same Docker network so `k6` can target the BFF by container name.

k6 tips:
- On macOS/arm64, if the `grafana/k6` image is incompatible, either install `k6` locally or run the k6 container with `--platform linux/amd64`.
- Example run (inside the staging script we run k6 against the container name):

```bash
# manual k6 run example (network created by staging script)
docker run --rm --network greenai-net -e TARGET_URL=http://greenai-staging-bff:8000 grafana/k6 run /path/to/k6_script.js
```

## Developer workflow notes

- Use `.venv_py311` for any CI parity testing locally.
- Run linters/tests before making commits.
- The repo contains `scripts/run_staging_load.sh` to perform an end-to-end staging run — inspect logs under `logs/` if present.

## Next steps (optional)

- Commit the chosen DEV_SETUP file locally and create a branch prefixed with `chore/dev-setup/` when ready to push.
- If you'd like, I can also add a short GitHub Actions workflow skeleton for local gated checks (lint/test/audit) — tell me to proceed.
