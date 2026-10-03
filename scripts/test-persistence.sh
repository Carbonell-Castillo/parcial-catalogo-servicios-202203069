#!/bin/sh
set -eu
before=$(docker compose exec -T db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -tAc "select count(*) from usuario;"')
docker compose restart
after=$(docker compose exec -T db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -tAc "select count(*) from usuario;"')
if [ "$before" != "$after" ] || [ "$after" -lt 2 ]; then
  echo "P12 falló: antes=$before después=$after" >&2
  exit 1
fi
echo "P12 OK: $after usuarios persisten después del reinicio"
