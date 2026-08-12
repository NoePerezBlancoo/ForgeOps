# Proceso de release

## Flujo

1. Crear `feature/*` desde `main` y mantener commits pequenos.
2. Abrir PR; `Quality gate` debe completar backend, frontend, seguridad y builds Docker.
3. Revisar migraciones, cambios de variables y compatibilidad hacia atras.
4. Fusionar a `main`; el workflow despliega staging si dispone de credenciales.
5. Ejecutar smoke test de staging: health, ready, login, tenant A/B, operador, trial, storage, worker y PWA.
6. Actualizar version y notas; crear tag firmado o protegido `v1.2.1`.
7. Ejecutar `Release production`, aprobar el environment y validar healthchecks.
8. Observar errores, latencia y jobs durante 30 minutos.

## Comandos de validacion

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
docker compose build
```

## Migraciones

- Cada revision debe tener `upgrade` y `downgrade` revisables.
- No mezclar eliminacion de columnas con el primer deploy que deja de usarlas.
- Crear indices grandes de forma compatible con la carga esperada.
- El pre-deploy utiliza credenciales de migracion; el proceso web no las necesita.
- Si `python -m scripts.check_migrations` falla, la API no arranca.

## Rollback

Un rollback de codigo solo es valido si la migracion es compatible con la version anterior. Railway puede redeplegar el artefacto previo. Para datos, usar el runbook de recuperacion y nunca improvisar `downgrade` sobre produccion.

## Criterio de salida

La release se considera promovida cuando `/ready` responde 200, el frontend carga, el login cliente y operador funcionan, se completa un job de prueba y no aparecen errores nuevos. Registrar commit, revision Alembic, hora, operador y resultado.
