#!/bin/sh
set -eu

if [ "${APP_ENV:-development}" = "production" ]; then
  if [ "${SEED_DEMO_DATA:-false}" = "true" ] || [ "${ALLOW_DEMO_SEED:-false}" = "true" ]; then
    echo "La carga demo debe estar desactivada en produccion" >&2
    exit 1
  fi
fi

if [ "${SEED_DEMO_DATA:-false}" = "true" ] && [ "${ALLOW_DEMO_SEED:-true}" != "true" ]; then
  echo "SEED_DEMO_DATA requiere ALLOW_DEMO_SEED=true" >&2
  exit 1
fi

if [ "${RUN_MIGRATIONS:-true}" = "true" ]; then
  alembic upgrade head
else
  python -m scripts.check_migrations
fi

if [ "${RUN_RUNTIME_ROLE_SETUP:-false}" = "true" ]; then
  python -m scripts.ensure_runtime_role
fi

if [ "${SEED_DEMO_DATA:-false}" = "true" ]; then
  python -m scripts.seed_demo
fi

exec uvicorn app.main:app \
  --host 0.0.0.0 \
  --port "${PORT:-8000}" \
  --timeout-graceful-shutdown "${GRACEFUL_SHUTDOWN_SECONDS:-30}"
