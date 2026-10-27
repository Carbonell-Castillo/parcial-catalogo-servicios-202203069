#!/bin/sh
set -eu
db_count() { docker compose exec -T app python -m app.cli counts; }
before=$(db_count)
docker compose restart
after=""
i=0
while [ "$i" -lt 45 ]; do
  after=$(db_count 2>/dev/null || true)
  if [ -n "$after" ] && curl -fsS "http://localhost:${APP_PORT:-8000}/health" >/dev/null 2>&1; then break; fi
  i=$((i+1)); sleep 2
done
[ -n "$after" ] && [ "$before" = "$after" ] || { echo "P18 falló: antes=$before después=$after" >&2; exit 1; }
echo "P18 OK (servicios, CI, tickets, historial): $after"
