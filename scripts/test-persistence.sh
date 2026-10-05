#!/bin/sh
set -eu
before=$(docker compose exec -T db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -tAc "select count(*) from usuario;"')
docker compose restart
after=""
for attempt in $(seq 1 45); do
  candidate=$(docker compose exec -T db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -tAc "select count(*) from usuario;"' 2>/dev/null || true)
  if [ -n "$candidate" ] && curl -fsS "http://localhost:${APP_PORT:-8000}/health" >/dev/null 2>&1; then
    after=$candidate
    break
  fi
  sleep 2
done
if [ -z "$after" ]; then
  echo "P12 falló: los servicios no recuperaron salud después del reinicio" >&2
  exit 1
fi
if [ "$before" != "$after" ] || [ "$after" -lt 2 ]; then
  echo "P12 falló: antes=$before después=$after" >&2
  exit 1
fi
echo "P12 OK: $after usuarios persisten después del reinicio"
