# Service Desk y CMDB

Aplicación web local que conserva el catálogo y la organización del parcial, e incorpora tickets, siete procesos, colas, permisos, auditoría y una CMDB reproducible de 5,000 dispositivos.

**Estudiante:** Bruce Carbonell Castillo Cifuentes · **Carnet:** 202203069

## Ejecución desde un clon limpio

Requiere Docker con Compose v2 y puerto 8000. No requiere Python, Node, IA ni claves externas.

```powershell
Copy-Item .env.example .env
docker compose up --build -d
docker compose exec -T app python -m app.cli import data/CatalogoServicios.xlsx
docker compose exec -T app python -m app.cli generate-cmdb --count 5000 --seed 20261028
docker compose exec -T app python -m app.cli seed-tickets
docker compose ps
```

Abra http://localhost:8000. Salud: http://localhost:8000/health. El arranque migra y crea cuentas, roles operativos, siete colas y artículos de autoservicio idempotentemente.

| Perfil | Usuario | Contraseña demo |
|---|---|---|
| Administrador | `admin` | `Admin-Demo-2026!` |
| Consulta | `consulta` | `Consulta-Demo-2026!` |
| Solicitante | `solicitante` | `Solicitante-Demo-2026!` |
| Agente | `agente` | `Agente-Demo-2026!` |
| Aprobador | `aprobador` | `Aprobador-Demo-2026!` |

## Validación

```powershell
docker compose run --rm --no-deps --entrypoint pytest app -q --disable-warnings
powershell -ExecutionPolicy Bypass -File scripts/validate.ps1
```

En Bash: `sh scripts/validate.sh`. API: `/docs`. Adjuntos: PDF, PNG, JPEG o texto, máximo 5 MiB.

## Operación

```powershell
docker compose logs -f app db
docker compose restart
docker compose down
```

`down` conserva el volumen. `docker compose down -v` destruye deliberadamente datos y solo debe usarse para reiniciar pruebas. Los Excel se leen, no se modifican.

## Documentación

- [Resolución](docs/RESOLUCION.md)
- [Modelo y fuentes](docs/MODELO.md)
- [Procesos](docs/PROCESOS.md)
- [Ingeniería IA](docs/IA.md)
- [Pruebas](docs/PRUEBAS.md)

No se realizaron commits ni etiquetas, por instrucción expresa del usuario.
