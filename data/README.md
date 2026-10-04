# Fuente de datos

Este directorio conserva los archivos proporcionados sin modificarlos:

- `CatalogoServicios.xlsx` — SHA-256 `DE3B478A5FAEEEAEBCE1AA7726E0E3321188A68E41BBB656E1D17B0C5B74DCF0`.
- `plantilla-raci-ejemplo.xlsx` — SHA-256 `2B825D378446FE733EAE097D4EF2CAE9510F978DB29BC153CD81D19E1EC77745`.

La plantilla RACI es referencia; la matriz del proyecto está en `docs/MATRIZ_RACI.md`.

El directorio se monta como solo lectura dentro del contenedor. Para repetir la importación, ejecute:

```bash
docker compose exec -T app python -m app.cli import data/CatalogoServicios.xlsx
```
