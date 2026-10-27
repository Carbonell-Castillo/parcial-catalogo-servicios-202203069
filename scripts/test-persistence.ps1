$ErrorActionPreference = 'Stop'
$before = docker compose exec -T app python -m app.cli counts
if ($LASTEXITCODE -ne 0 -or -not $before) { throw 'P18 no pudo leer conteos iniciales' }
docker compose restart
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
$after = $null
foreach ($attempt in 1..45) {
  $candidate = docker compose exec -T app python -m app.cli counts 2>$null
  if ($LASTEXITCODE -eq 0 -and $candidate) {
    try { if ((Invoke-RestMethod http://localhost:8000/health -TimeoutSec 3).status -eq 'ok') { $after=$candidate; break } } catch {}
  }
  Start-Sleep -Seconds 2
}
if (-not $after -or $before.Trim() -ne $after.Trim()) { throw "P18 falló: antes=$before después=$after" }
$n=$after.Trim().Split(',')
if ([int]$n[0] -lt 46 -or [int]$n[1] -lt 5000 -or [int]$n[2] -lt 35 -or [int]$n[3] -lt 35) { throw "P18 conteos insuficientes: $after" }
Write-Output "P18 OK (servicios, CI, tickets, historial): $after"
