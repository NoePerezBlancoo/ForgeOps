# Runbook de produccion

## Comprobacion diaria

1. Abrir `/control` y revisar empresas, cola y jobs fallidos.
2. Consultar `/ready`; database y Redis deben estar disponibles.
3. Revisar errores 5xx, p95 de latencia, reinicios y consumo de recursos en Railway.
4. Confirmar que el ultimo backup y el archivo PITR estan vigentes.
5. Revisar fallos SMTP, indexacion documental y crecimiento del bucket.

## API no disponible

```bash
curl -i https://api.forgeops.es/health
curl -i https://api.forgeops.es/ready
railway logs --service backend --environment production
railway logs --service worker --environment production
```

- `/health` falla: revisar crash, variables y ultimo deploy; hacer rollback de artefacto.
- `/health` funciona y `/ready` falla: revisar PostgreSQL y Redis sin reiniciar datos.
- Conservar el `X-Request-ID` del error y buscarlo en logs/Sentry.
- Activar `MAINTENANCE_MODE=true` si las escrituras no son seguras. `/control` y healthchecks permanecen accesibles.

## Cola detenida

1. Confirmar `PING` de Redis y estado del worker.
2. Revisar `background_jobs` en `PENDING`, `QUEUED` y `FAILED`.
3. Corregir dependencia externa antes de reintentar.
4. Reiniciar el worker; al arrancar redistribuye jobs pendientes.
5. No duplicar jobs manualmente: la clave de idempotencia protege el efecto logico.

## Storage degradado

1. Comprobar credenciales y endpoint del bucket.
2. Confirmar que la hora del contenedor es correcta para firmas S3.
3. No cambiar a storage local en produccion.
4. Mantener los registros de documento; reintentar la operacion cuando S3 se recupere.

## Migracion fallida

1. Detener promocion de la release y activar mantenimiento.
2. Leer el error de pre-deploy; la version anterior sigue activa si el healthcheck no promociona.
3. Para una migracion compatible, corregirla hacia delante.
4. Para corrupcion o cambio destructivo, restaurar PITR en un servicio nuevo.
5. Validar revision Alembic, recuentos, RLS, login y documentos antes de cambiar trafico.

## Incidente de seguridad

1. Suspender cuentas o empresa afectada desde `/control`.
2. Rotar `SECRET_KEY` solo con un plan de invalidacion de sesiones; rotar credenciales comprometidas inmediatamente.
3. Preservar auditoria, request IDs y logs con acceso restringido.
4. Determinar empresas y periodo afectados sin acceder a contenido industrial innecesario.
5. Documentar acciones y cumplir el proceso legal aplicable.

## Escalado

Backend y frontend son stateless y admiten multiples replicas. Aumentar worker por profundidad y edad de cola. Antes de escalar backend, confirmar limites PgBouncer/PostgreSQL. Las sesiones se almacenan en PostgreSQL y no requieren afinidad.
