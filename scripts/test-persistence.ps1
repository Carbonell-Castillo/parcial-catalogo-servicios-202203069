$ErrorActionPreference = 'Stop'
$countCommand = 'psql -U \"$POSTGRES_USER\" -d \"$POSTGRES_DB\" -tAc \"select count(*) from usuario;\"'
$before = docker compose exec -T db sh -c $countCommand
if ($LASTEXITCODE -ne 0) { throw 'P12 no pudo leer el conteo inicial' }
docker compose restart
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
$after = $null
foreach ($attempt in 1..45) {
  $candidate = docker compose exec -T db sh -c $countCommand 2>$null
  if ($LASTEXITCODE -eq 0 -and $candidate) {
    try {
      $health = Invoke-RestMethod -Uri 'http://localhost:8000/health' -TimeoutSec 3
      if ($health.status -eq 'ok') { $after = $candidate; break }
    } catch {}
  }
  Start-Sleep -Seconds 2
}
if ($null -eq $after) { throw 'P12 falló: los servicios no recuperaron salud después del reinicio' }
if ($before.Trim() -ne $after.Trim() -or [int]$after -lt 2) { throw "P12 falló: antes=$before después=$after" }
Write-Output "P12 OK: $after usuarios persisten después del reinicio"
