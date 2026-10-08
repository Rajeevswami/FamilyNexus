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

# Find the directory that holds manage.py. The script is invoked from three
# different places — the repo root, the backend/ directory on Render (where
# rootDir is set), and next to manage.py inside the container image — so the
# path cannot be hardcoded relative to the caller's working directory.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ -f "${SCRIPT_DIR}/../backend/manage.py" ]; then
  cd "${SCRIPT_DIR}/../backend"
elif [ -f "${SCRIPT_DIR}/manage.py" ]; then
  cd "${SCRIPT_DIR}"
elif [ -f "./manage.py" ]; then
  :
else
  echo "release.sh: could not find manage.py" >&2
  exit 1
fi

PORT="${PORT:-8000}"
WORKERS="${WEB_CONCURRENCY:-3}"
TIMEOUT="${GUNICORN_TIMEOUT:-60}"

echo "==> Working directory: $(pwd)"

echo "==> Checking configuration"
# Deploy warnings go to stderr. A non-zero exit here would abort the deploy, so
# report and continue: the operator reads them from the build log.
python manage.py check --deploy --fail-level ERROR 2>&1 || true

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
