#!/bin/sh
set -e

host="${POSTGRES_HOST:-postgres}"
port="${POSTGRES_PORT:-5432}"

until python -c "import socket; s=socket.socket(); s.settimeout(1); s.connect(('${host}', ${port})); s.close()" 2>/dev/null; do
  echo "waiting for postgres at ${host}:${port}..."
  sleep 1
done

alembic upgrade head
exec "$@"
