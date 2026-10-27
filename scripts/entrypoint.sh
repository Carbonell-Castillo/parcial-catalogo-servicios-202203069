#!/bin/sh
set -eu
alembic upgrade head
python -m app.cli seed
python -m app.cli seed-service-desk
exec uvicorn app.main:app --host 0.0.0.0 --port 8000

