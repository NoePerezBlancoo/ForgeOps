# ForgeOps 1.2.3 - Production Deployment Foundation

## Proposito

ForgeOps 1.2.3 convierte el despliegue en un proceso verificable. La promocion deja de comprobar solo que dos URLs responden: valida que backend y frontend pertenecen a la version y commit esperados, que las dependencias obligatorias estan disponibles y que el artefacto etiquetado mantiene metadatos coherentes.

## Alcance

- Version de aplicacion 1.2.3 alineada en backend, frontend, contenedores, Compose y ejemplos de entorno.
- Smoke test comun para staging y produccion en `backend/scripts/validate_release.py`.
- Validacion de `/health`, `/ready`, `X-Request-ID` y `/login`.
- Comparacion de version, entorno y commit desplegados.
- Preflight de formato de version, tag y metadatos antes del environment protegido de produccion.
- Timeouts explicitos para impedir ejecuciones de despliegue indefinidas.
- Roadmap comercial y ADR de trazabilidad de intervenciones versionados.
- Intervenciones multi-tecnico con sesiones, notas, historial inmutable y validacion responsable.
- Centro de ordenes responsive con acciones operativas, equipo, tiempos y cierre controlado.
- Invitaciones de empleados con activacion de un solo uso y conservacion del historial.
- Notificaciones in-app para asignaciones e incidencias criticas con centro responsive.

## Estado de validacion

| Control | Estado | Evidencia requerida |
| --- | --- | --- |
| PR #8 y orquestador local | `TESTED` | Fusion y Quality Gate verde en `main` |
| Smoke validator | `TESTED` | Ruff y pruebas unitarias ejecutadas |
| Workflows staging/production | `IMPLEMENTED` | Revision de sintaxis y Quality Gate del PR |
| Trazabilidad de intervenciones | `TESTED` | Suite API, migracion real, RLS, Redis y revision responsive |
| Usuarios e invitaciones | `TESTED` | Token SHA-256, limites, aceptacion, revocacion, RLS y revision responsive |
| Notificaciones in-app | `TESTED` | OT asignada, incidencia critica, destinatario, lectura y enlaces profundos |
| Staging V1.2.2 | `STAGING_VALIDATED` | Release validator remoto con health, readiness y frontend |
| Staging V1.2.3 | `EXTERNAL_BLOCKER` | `RAILWAY_STAGING_ENABLED=false` |
| PostgreSQL/RLS y worker local | `TESTED` | PostgreSQL 17, rol runtime y roundtrip Redis ejecutados |
| Storage y MFA | `TESTED` | Suite automatizada local |
| Backups y PITR | `EXTERNAL_BLOCKER` | Captura/configuracion del proveedor y restore no productivo |
| Produccion | `EXTERNAL_BLOCKER` | Aprobacion de cutover y environment configurado |

## Preflight de release

Antes de crear el tag:

```powershell
docker compose exec -T backend ruff check app scripts tests alembic
docker compose exec -T backend pytest
docker compose exec -T backend alembic check
docker compose exec -T backend python -m scripts.check_migrations
docker compose exec -T frontend npm run lint
docker compose exec -T frontend npm run typecheck
docker compose exec -T frontend npm test
docker compose exec -T frontend npm run build
docker compose config --quiet
```

Despues del despliegue, el workflow ejecuta el equivalente a:

```powershell
$env:RELEASE_API_URL = "https://backend.example"
$env:RELEASE_APP_URL = "https://frontend.example"
$env:EXPECTED_VERSION = "1.2.3"
$env:EXPECTED_ENVIRONMENT = "staging"
$env:EXPECTED_COMMIT = (git rev-parse HEAD)
python backend/scripts/validate_release.py
```

La validacion profunda de staging sigue siendo obligatoria:

```powershell
docker compose run --rm backend python -m scripts.validate_staging
```

Debe ejecutarse con las variables y servicios reales de staging, nunca con datos productivos.

## Promocion

1. Fusionar el PR solo con todos los jobs verdes.
2. Desplegar `main` en staging y guardar commit, fecha y resultado de ambos validadores.
3. Mantener staging en observacion antes del tag.
4. Crear `v1.2.3` desde el mismo commit validado.
5. Ejecutar manualmente `Release production` con `version=1.2.3`.
6. Aprobar el environment de produccion solo tras revisar backup/PITR, rollback y ventana.
7. Observar salud, errores, latencia y cola durante al menos 30 minutos.

## Rollback

Si falla el preflight o el despliegue no alcanza readiness, no se promociona trafico. Si falla despues de promocionar, Railway debe redeplegar el artefacto anterior siempre que la migracion siga siendo compatible. Un problema de integridad o una migracion destructiva requiere restauracion a un servicio PostgreSQL nuevo y validacion antes de cambiar referencias.

No se ejecuta `alembic downgrade` improvisado ni se restaura sobre la base de datos origen.

## Bloqueos externos actuales

- GitHub variable `RAILWAY_STAGING_ENABLED` esta desactivada.
- La configuracion real de backups/PITR y un ensayo de restore requieren acceso operativo al proyecto Railway.
- Dominios, DNS, SMTP y Sentry requieren servicios o credenciales del propietario.
- El cutover final de produccion requiere autorizacion expresa.
