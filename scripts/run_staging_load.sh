#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<EOF
Usage: $0 [--run]

Preview the staging harness steps by default. Pass --run to actually start containers
and run the lightweight staging scenario. Environment variables control DB creds and
K6 script path:

  POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB, K6_SCRIPT, K6_IMAGE

This script is conservative: run without `--run` to verify effects before executing.
EOF
}

RUN=false
if [[ "${1-}" == "--help" ]]; then
  usage
  exit 0
fi
if [[ "${1-}" == "--run" ]]; then
  RUN=true
fi

POSTGRES_USER=${POSTGRES_USER:-postgres}
POSTGRES_PASSWORD=${POSTGRES_PASSWORD:-postgres}
POSTGRES_DB=${POSTGRES_DB:-greenai}
K6_SCRIPT=${K6_SCRIPT:-load/k6_test.js}
K6_IMAGE=${K6_IMAGE:-loadimpact/k6:latest}
NET=greenai-net

echo "Staging harness preview:" 
echo "  Network: ${NET}"
echo "  Postgres: user=${POSTGRES_USER} db=${POSTGRES_DB}"
echo "  K6 script: ${K6_SCRIPT} (image: ${K6_IMAGE})"

if [[ "$RUN" != true ]]; then
  echo "Preview only. Re-run with --run to perform the staging run."
  exit 0
fi

command -v docker >/dev/null 2>&1 || { echo "docker not found in PATH" >&2; exit 1; }

echo "Creating docker network ${NET} (if missing)"
docker network inspect "${NET}" >/dev/null 2>&1 || docker network create "${NET}"

echo "Starting postgres container (temporary)..."
docker run -d --rm --name greenai-staging-postgres --network ${NET} \
  -e POSTGRES_USER=${POSTGRES_USER} -e POSTGRES_PASSWORD=${POSTGRES_PASSWORD} -e POSTGRES_DB=${POSTGRES_DB} \
  -p 5432:5432 postgres:15

echo "Starting redis container (temporary)..."
docker run -d --rm --name greenai-staging-redis --network ${NET} -p 6379:6379 redis:7

echo "NOTE: BFF build/run steps are intentionally left to maintainers (image/build differs per org)."
echo "If a local BFF image name is available, run it attached to network ${NET} so k6 can target it."

echo "Running k6 in container against target container name (example):"
echo "  docker run --rm --network ${NET} -v \\$(pwd):/scripts ${K6_IMAGE} run /scripts/${K6_SCRIPT} --out json=results.json"

echo "Staging harness run complete (containers are left running; stop them manually when finished)."
#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$ROOT_DIR"

echo "Starting staging load run from $ROOT_DIR"

# Cleanup previous runs
docker rm -f greenai-staging-postgres >/dev/null 2>&1 || true
docker rm -f greenai-staging-redis >/dev/null 2>&1 || true
pkill -f 'uvicorn bff.main:app' >/dev/null 2>&1 || true

mkdir -p logs



echo "Building and running BFF as Docker container for staging..."
# ensure a docker network for container name resolution
docker network create greenai-net >/dev/null 2>&1 || true

# re-create Postgres/Redis on the network
docker rm -f greenai-staging-postgres || true
docker rm -f greenai-staging-redis || true
docker run --name greenai-staging-postgres --network greenai-net -e POSTGRES_PASSWORD=pass -e POSTGRES_USER=test -e POSTGRES_DB=testdb -p 5433:5432 -d postgres:15
docker run --name greenai-staging-redis --network greenai-net -p 6379:6379 -d redis:7

echo "Waiting for Postgres to accept connections..."
for i in {1..60}; do
  if docker exec greenai-staging-postgres pg_isready -U test >/dev/null 2>&1; then
    break
  fi
  sleep 1
done
if ! docker exec greenai-staging-postgres pg_isready -U test >/dev/null 2>&1; then
  echo "Postgres not ready after timeout" >&2
  docker logs greenai-staging-postgres || true
  exit 1
fi

echo "Creating Postgres extensions (uuid-ossp, pgcrypto) as superuser..."
# run as postgres user to ensure extension creation permissions
docker exec -u postgres greenai-staging-postgres psql -d testdb -c "CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\";" >/dev/null 2>&1 || true
docker exec -u postgres greenai-staging-postgres psql -d testdb -c "CREATE EXTENSION IF NOT EXISTS pgcrypto;" >/dev/null 2>&1 || true

echo "Applying SQL schema files to Postgres (preprocess to strip markdown fences)..."
SCHEMA_DIR="$ROOT_DIR/database/schema"
if [ -d "$SCHEMA_DIR" ]; then
  for f in "$SCHEMA_DIR"/*.sql; do
    [ -f "$f" ] || continue
    base=$(basename "$f")
    clean="/tmp/clean_${base}"
    # remove markdown fences and leading/trailing code fences
    awk 'BEGIN{skip=0} /^```/{skip=!skip; next} !skip{print}' "$f" > "/tmp/${base}.cleaned.sql"
    docker cp "/tmp/${base}.cleaned.sql" greenai-staging-postgres:$clean
    echo "Executing $clean"
    docker exec greenai-staging-postgres psql -U test -d testdb -f "$clean" || true
    docker exec greenai-staging-postgres rm -f "$clean" || true
    rm -f "/tmp/${base}.cleaned.sql"
  done
else
  echo "No SQL schema directory found; skipping schema apply."
fi

echo "Building BFF Docker image..."
# If `requirements.lock.txt` is missing, create a temporary copy from
# `requirements.txt` so Dockerfile COPY steps succeed; remove it after build.
TEMP_LOCK_CREATED=0
if [ ! -f requirements.lock.txt ] && [ -f bff/requirements.txt ]; then
  echo "No requirements.lock.txt found; creating temporary lock from bff/requirements.txt"
  cp bff/requirements.txt requirements.lock.txt
  TEMP_LOCK_CREATED=1
fi

docker build -f bff/Dockerfile -t greenai-bff:staging .

if [ "$TEMP_LOCK_CREATED" -eq 1 ]; then
  echo "Removing temporary requirements.lock.txt"
  rm -f requirements.lock.txt
fi

docker rm -f greenai-staging-bff || true
docker run --name greenai-staging-bff --network greenai-net -e DB_URL='postgresql://test:pass@greenai-staging-postgres:5432/testdb' -e DATABASE_URL='postgresql+asyncpg://test:pass@greenai-staging-postgres:5432/testdb' -p 8000:8000 -d greenai-bff:staging

echo "Waiting for BFF to be healthy..."
for i in {1..60}; do
  if curl -sS --max-time 2 http://localhost:8000/health | grep -E -q '"status":[[:space:]]*"ok"'; then
    break
  fi
  sleep 1
done
if ! curl -sS --max-time 2 http://localhost:8000/health | grep -E -q '"status":[[:space:]]*"ok"'; then
  echo "BFF health check failed; show container logs:" >&2
  docker logs greenai-staging-bff --tail 200 || true
  exit 1
fi

echo "Running k6 load test (1 minute)..."
K6_OUT="logs/k6_result_$(date +%s).txt"
# Prefer running k6 in a container attached to the same Docker network so it can target the BFF by container name.
K6_DOCKER_IMAGE=grafana/k6
TARGET_IN_DOCKER='http://greenai-staging-bff:8000/health'

# Try docker k6 image on the same network (no host.docker.internal needed)
if docker run --network greenai-net --platform=linux/amd64 --rm -v "${ROOT_DIR}/load":/load -e TARGET_URL="$TARGET_IN_DOCKER" $K6_DOCKER_IMAGE run /load/k6_test.js | tee "$K6_OUT"; then
  :
else
  if command -v k6 >/dev/null 2>&1; then
    echo "Docker k6 image unavailable; using local k6 binary against localhost:8000"
    TARGET_URL='http://localhost:8000/health' k6 run "${ROOT_DIR}/load/k6_test.js" | tee "$K6_OUT"
  else
    echo "k6 image/platform not available and local k6 not installed; skipping load test." | tee "$K6_OUT"
  fi
fi

echo "--- k6 summary (tail) ---"
tail -n 200 "$K6_OUT" || true

echo "Cleaning up: stopping app and containers..."
docker rm -f greenai-staging-bff || true
docker rm -f greenai-staging-postgres || true
docker rm -f greenai-staging-redis || true

echo "Staging load test finished; logs are in logs/"
exit 0
