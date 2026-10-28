# Evidencia del ciclo de harness

Índice general: [../IA.md](../IA.md). Ciclos con todos sus campos: [LOOPS.md](LOOPS.md).

Las secciones "Ciclo real" a "Ciclo de interfaz real" se escribieron el 2026-10-01, cuando el proyecto aún no tenía Git (por instrucción expresa en ese momento). Su estado resultante quedó versionado después: scripts en [`7292148`](https://github.com/Carbonell-Castillo/parcial-catalogo-servicios-202203069/commit/7292148d733611481d1c531d28ee5535d6c94c49), código en [`edbe5fc`](https://github.com/Carbonell-Castillo/parcial-catalogo-servicios-202203069/commit/edbe5fc68ad50109fcab27cb9af2234e4c3d9999), pruebas en [`9e1f5e5`](https://github.com/Carbonell-Castillo/parcial-catalogo-servicios-202203069/commit/9e1f5e5be0f0499db6816fd0f16b25905bff211b) y correcciones finales en [`2ea52a5`](https://github.com/Carbonell-Castillo/parcial-catalogo-servicios-202203069/commit/2ea52a53c8fb15eb546e71ae21a31fb815ac1649) (etiqueta `parcial-v2.0`).

## Ciclo real

1. Tarea: implementar autenticación, organización, servicios e importador.
2. Cambio propuesto por IA: modelo y API con sesiones revocables.
3. Control ejecutado dentro de la imagen Docker:

```bash
docker compose run --rm --no-deps --entrypoint pytest app -q --disable-warnings
```

4. Fallo real detectado: `8 failed, 2 passed, 1 skipped`; `NameError: timezone is not defined` en `app/security.py` al normalizar fechas devueltas por SQLite.
5. Corrección: importar `timezone` y conservar la normalización solo para el backend SQLite de pruebas.
6. Nueva ejecución: `10 passed, 1 skipped` en 2.53 s. El skip fue la prueba del Excel original ausente, no un fallo oculto.

Después de las revisiones se ejecutó la suite ampliada: `11 passed, 1 skipped` en 3.46 s. También se levantó PostgreSQL real, `/health` respondió `ok`, el login devolvió rol `administrador`, la jerarquía demo contenía una empresa y P12 informó `2 usuarios persisten después del reinicio`.

## Ciclo adicional con el Excel real

1. Primera carga: fallo `UniqueViolation` para `SE.01.01`; C5:C7 era una combinación y sus filas de continuación se trataban como altas.
2. Corrección: reconocer el ancla de la combinación C y omitir continuaciones. Se añadió una prueba de regresión específica.
3. Nueva carga: 12 N1/45 N2; el control de calidad detectó que faltaba uno.
4. Investigación: la fila 101 contiene el código explícito `SE.12.3`, pero A/B vacías fuera de combinación.
5. Corrección: regla explícita y observada que vincula solo fila 101/`SE.12.3` con `SE.12`.
6. Resultado desde volumen limpio: lote 1 con `creados=58` (12 N1 + 46 N2), 51 filas omitidas/continuación y cuatro observaciones. Lote 2: 0 creados, 0 actualizados, 97 omitidos, cuatro observaciones, 12/46. La base contiene tres asignaciones responsables válidas.
7. Suite final con el archivo original presente: `13 passed` en 4.47 s, sin skips.
8. Auditoría final Claude Engineer: `PASS`; confirmó que la omisión se limita a filas no-ancla de C combinada y que la inferencia se limita exactamente a fila 101/`SE.12.3`, sin propagación genérica.

## Ciclo de interfaz real

1. Reporte: las pestañas, búsqueda de Servicios y botón Volver parecían no reaccionar.
2. Reproducción en Chrome con Playwright: las pestañas cargaban, pero buscar conservaba la tabla anterior.
3. Causa: el formulario enviaba filtros opcionales vacíos (`nivel1_id=&clase_id=...`); FastAPI respondió 422 y el frontend no mostraba ese rechazo.
4. Corrección: construir la query solo con valores no vacíos, mostrar estado de carga/error en pestañas y reemplazar handlers inline de Volver/Cancelar por listeners explícitos.
5. Prevención: `tests/e2e/frontend.spec.js` recorre login, Organización, Usuarios, Catálogos, Importaciones, Servicios, búsqueda `SE.12.3`, ficha y Volver.
6. Resultado final después de reiniciar: backend `13 passed`, P12 OK y Playwright `1 passed`; `app` y `db` healthy.
7. El primer `scripts/validate.ps1` integrado detectó una carrera: Compose devolvía control antes de que `/health` aceptara conexiones. Se añadieron reintentos de hasta 90 segundos en PowerShell y Bash. La repetición completa terminó con código 0, `13 passed`, importación real idempotente 12/46 y Playwright `1 passed`.
8. La edición dejó de usar `prompt()` o reemplazar la vista: se añadió una modal nativa reutilizable para servicios, organización, usuarios y catálogos. El E2E abre/cancela todas las variantes y guarda/restaura una edición organizacional real.

## Límites operativos

- No leer ni publicar secretos de `.env`.
- No modificar el Excel original; Docker lo monta `:ro`.
- No usar `docker compose down -v` salvo reinicio deliberado de datos de prueba.
- Los tests usan SQLite aislado; P12 usa PostgreSQL real y reinicio de contenedores.
- El sistema funciona sin Claude, API keys ni suscripción de IA.

## Harness V4 — Service Desk y CMDB

Commit: `SHA-V4-PENDIENTE` (cambios en el árbol de trabajo, sin commit por instrucción).

### Etapas de `scripts/validate.ps1` / `validate.sh`

Cada etapa que devuelve un código ≠ 0 detiene la rutina.

| # | Etapa | Comando | Qué detecta |
|---|---|---|---|
| 1 | Construir | `docker compose --profile test build` | Dependencias, imagen E2E desactualizada |
| 2 | Pruebas aisladas | `docker compose run --rm --no-deps --entrypoint pytest app -q --disable-warnings` | Lógica de API, importador, Service Desk y CMDB (SQLite en memoria) |
| 3 | Levantar | `docker compose up --build -d` (el entrypoint ejecuta `alembic upgrade head`, `seed` y `seed-service-desk`) | Migraciones, seeds |
| 4 | Salud | `/health` con reintentos de hasta 90 s | Arranque, conexión a PostgreSQL |
| 5 | Importar catálogo | `python -m app.cli import data/CatalogoServicios.xlsx` | Control 12/46 con el Excel real |
| 6 | Generar CMDB | `python -m app.cli generate-cmdb --count 5000 --seed 20261028` | 5,000 CI únicos; repetir con la misma semilla crea 0 |
| 7 | Tickets demo | `python -m app.cli seed-tickets` | ≥35 tickets, E0–E3, I0–I6 |
| 8 | E2E | `docker compose --profile test run --rm e2e` | Interfaz real en Chromium |
| 9 | Persistencia (P18) | `scripts/test-persistence.ps1` | Catálogo, CMDB, tickets e historial tras `docker compose restart` |

### Controles de secretos y límites

- `.env` excluido por `.gitignore` y `.dockerignore`; `.env.example` sin secretos reales; AGENTS.md prohíbe leer o publicar `.env`.
- Los Excel se montan `:ro`; las pruebas no los alteran.
- Las pruebas usan SQLite en memoria; la base de evaluación (PostgreSQL) no se toca.
- `down -v` solo para reiniciar datos de prueba; el arranque normal nunca borra datos.
- Límites de operación: adjuntos de 5 MiB como máximo, recorrido de grafo de 1,000 CI como máximo, página de 200 como máximo.

### Resultados

| Fecha | Comando | Base | Resultado |
|---|---|---|---|
| 2026-10-27 | `scripts/validate.ps1` | Árbol V4 sin commit | `26 passed`, Playwright `1 passed`, 12/46 sin duplicados, CMDB 5000 (2500 Hardware y 2500 Software), 37 tickets, `P18 OK (46,5000,37,37)`. Antes, una corrida falló por el índice de prioridad (ciclo L5). Fuente: [RESOLUCION §11](../RESOLUCION.md) |
| 2026-10-29 | `docker compose build app` + `docker compose run --rm --no-deps --entrypoint pytest app -q --disable-warnings -p no:cacheprovider` | Árbol con cambios en stage sobre `2ea52a5` | `26 passed, 1 warning in 10.45s`, código de salida 0. En esta fecha no se ejecutaron E2E, importación ni P18 |
