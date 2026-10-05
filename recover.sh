#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

if [[ ! -f .env ]]; then
  cp .env.example .env
  echo "Created .env from .env.example"
else
  echo "Keeping existing .env"
fi

if [[ ! -d .venv ]]; then
  python -m venv .venv
fi

source .venv/bin/activate
python -m pip install -r requirements.txt

if docker ps -a --format '{{.Names}}' | grep -qx 'hexploration_postgres'; then
  echo "Existing hexploration_postgres container found; reusing it."
  if [[ "$(docker inspect -f '{{.State.Running}}' hexploration_postgres)" != "true" ]]; then
    docker start hexploration_postgres >/dev/null
    echo "Started existing hexploration_postgres container."
  fi
else
  echo "No existing hexploration_postgres container found; starting DB from compose.yml."
  docker compose up -d db
fi

echo "Waiting for PostgreSQL..."
for i in {1..30}; do
  if docker exec hexploration_postgres pg_isready -U hexploration -d hexploration >/dev/null 2>&1; then
    break
  fi
  sleep 1
  if [[ "$i" == "30" ]]; then
    echo "PostgreSQL did not become ready in time." >&2
    exit 1
  fi
done

alembic current || true
alembic heads
alembic upgrade head
alembic current

echo
python - <<'PY'
from db import Base
from db import models  # noqa: F401
print(f"DB metadata loaded: {len(Base.metadata.tables)} tables")
PY

echo
printf '%s\n' \
  'Recovery completed.' \
  'Start the API with:' \
  '  source .venv/bin/activate' \
  '  uvicorn main:app --reload'
