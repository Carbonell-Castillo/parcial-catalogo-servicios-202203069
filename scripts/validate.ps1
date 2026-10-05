$ErrorActionPreference = 'Stop'
docker compose --profile test build
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
docker compose run --rm --no-deps --entrypoint pytest app -q --disable-warnings
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
docker compose up --build -d
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
$ready = $false
$deadline = (Get-Date).AddSeconds(90)
do {
  try {
    $health = Invoke-RestMethod -Uri 'http://localhost:8000/health' -TimeoutSec 3
    if ($health.status -eq 'ok') { $ready = $true; break }
  } catch { Start-Sleep -Seconds 2 }
} while ((Get-Date) -lt $deadline)
if (-not $ready) {
  docker compose logs --no-color --tail 100 app
  throw 'La aplicación no alcanzó el estado saludable en 90 segundos'
}
if (Test-Path -LiteralPath 'data/CatalogoServicios.xlsx') {
  docker compose exec -T app python -m app.cli import data/CatalogoServicios.xlsx
  if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
} else {
  Write-Warning 'Importación real omitida: falta data/CatalogoServicios.xlsx'
}
docker compose --profile test run --rm e2e
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
powershell -ExecutionPolicy Bypass -File scripts/test-persistence.ps1
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
