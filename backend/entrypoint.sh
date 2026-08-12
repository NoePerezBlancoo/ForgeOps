#!/bin/sh
set -e

if [ "${APP_ENV:-development}" = "production" ] && [ "${SEED_DEMO_DATA:-false}" = "true" ]; then
  echo "SEED_DEMO_DATA no puede estar activo en produccion" >&2
  exit 1
fi

alembic upgrade head

if [ "${SEED_DEMO_DATA:-false}" = "true" ]; then
  python -m scripts.seed_demo
fi

exec uvicorn app.main:app --host 0.0.0.0 --port 8000
