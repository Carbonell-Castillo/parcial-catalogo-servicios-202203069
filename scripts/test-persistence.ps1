$ErrorActionPreference = 'Stop'
$before = docker compose exec -T db psql -U catalogo -d catalogo -tAc 'select count(*) from usuario;'
docker compose restart
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
$after = docker compose exec -T db psql -U catalogo -d catalogo -tAc 'select count(*) from usuario;'
if ($before.Trim() -ne $after.Trim() -or [int]$after -lt 2) { throw "P12 falló: antes=$before después=$after" }
Write-Output "P12 OK: $after usuarios persisten después del reinicio"
