# Evidencia del ciclo de harness

Fecha: 2026-10-01. Estado Git: sin commit por instrucción expresa del solicitante.

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
