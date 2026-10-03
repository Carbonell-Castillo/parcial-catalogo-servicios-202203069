#!/bin/sh
set -eu
docker compose build
docker compose run --rm --no-deps --entrypoint pytest app -q --disable-warnings
docker compose up --build -d
ready=0
for attempt in $(seq 1 45); do
  if curl -fsS "http://localhost:${APP_PORT:-8000}/health" >/dev/null 2>&1; then
    ready=1
    break
  fi
  sleep 2
done
if [ "$ready" -ne 1 ]; then
  docker compose logs --no-color --tail 100 app
  echo "La aplicación no alcanzó el estado saludable en 90 segundos" >&2
  exit 1
fi
if [ -f data/CatalogoServicios.xlsx ]; then
  docker compose exec -T app python -m app.cli import data/CatalogoServicios.xlsx
else
  echo "ADVERTENCIA: importación real omitida; falta data/CatalogoServicios.xlsx" >&2
fi
docker compose --profile test run --rm e2e
