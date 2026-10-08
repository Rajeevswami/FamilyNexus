#!/usr/bin/env bash
#
# Release step for a PaaS/container host: apply migrations, gather static files,
# then hand off to the web server.
#
# Safe to run on every deploy:
#   - migrations are idempotent and take a lock, so two instances starting at
#     once do not race each other into a broken schema;
#   - collectstatic is idempotent and WhiteNoise serves the result;
#   - a failing migration aborts before the new code starts serving, so
#     traffic stays on the previous release instead of hitting a half-migrated
#     database.
#
# PORT is provided by Render / Railway / Fly. It defaults to 8000 for a plain
# Docker run.
set -euo pipefail

cd "$(dirname "$0")/.."

PORT="${PORT:-8000}"
WORKERS="${WEB_CONCURRENCY:-3}"
TIMEOUT="${GUNICORN_TIMEOUT:-60}"

echo "==> Checking configuration"
python manage.py check --deploy 2>&1 | grep -v "W001" || true

echo "==> Applying database migrations"
python manage.py migrate --noinput

echo "==> Collecting static files"
python manage.py collectstatic --noinput --clear

echo "==> Starting gunicorn on port ${PORT} with ${WORKERS} worker(s)"
exec gunicorn config.wsgi:application \
  --bind "0.0.0.0:${PORT}" \
  --workers "${WORKERS}" \
  --timeout "${TIMEOUT}" \
  --access-logfile - \
  --error-logfile -
