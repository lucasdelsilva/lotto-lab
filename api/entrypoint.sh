#!/usr/bin/env bash
set -euo pipefail

echo "[entrypoint] aplicando migrations"
alembic upgrade head

echo "[entrypoint] iniciando: $*"
exec "$@"
