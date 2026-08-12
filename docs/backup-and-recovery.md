# Backup y recuperacion

Un backup no es fiable hasta haber sido restaurado y validado.

## Politica

- Activar PITR de Railway en PostgreSQL de produccion.
- Mantener backup incremental diario, semanal bloqueado y mensual exportado segun contrato y retencion.
- Conservar al menos una copia logica cifrada fuera del servicio primario.
- Aplicar ciclo equivalente al bucket de documentos mediante versionado/retencion del proveedor o exportacion separada.
- Staging tiene su propio backup y nunca recibe una copia productiva sin anonimizar.

Railway PITR crea backups base e historico WAL en un bucket y restaura en un servicio hermano; no modifica el origen. La retencion real depende de la configuracion contratada y debe comprobarse en el panel.

## Backup logico manual

Ejecutar desde una estacion autorizada sin incluir la clave en el historial:

```bash
pg_dump "$MIGRATION_DATABASE_URL" --format=custom --no-owner --no-acl --file forgeops-$(date +%Y%m%d-%H%M).dump
sha256sum forgeops-*.dump > forgeops-checksums.txt
```

Cifrar, subir al repositorio de backup, verificar checksum y registrar revision Alembic. No guardar dumps en Git ni en el contenedor de aplicacion.

## Restauracion de backup

1. Crear PostgreSQL nuevo y aislado, nunca sobrescribir el origen.
2. Restringir red y obtener una URL temporal.
3. Restaurar:

```bash
createdb "$RESTORE_DATABASE_NAME"
pg_restore --clean --if-exists --no-owner --no-acl --dbname "$RESTORE_DATABASE_URL" forgeops-YYYYMMDD-HHMM.dump
DATABASE_URL="$RESTORE_DATABASE_URL" alembic current
DATABASE_URL="$RESTORE_DATABASE_URL" alembic upgrade head
```

4. Crear el rol runtime, ejecutar `scripts.check_migrations` y la prueba RLS.
5. Arrancar una instancia ForgeOps aislada contra la DB restaurada.
6. Validar empresas, usuarios, plantas, activos, ordenes, auditoria, referencias de documentos y fechas.
7. Validar objetos del bucket con una muestra de cada empresa sin exponer datos entre tenants.
8. Hacer smoke test de login, lectura, escritura y job.
9. Solo entonces cambiar referencias de servicios y mantener el origen en solo lectura durante la ventana acordada.

## Restauracion PITR

1. Identificar el ultimo instante sano en UTC desde auditoria y logs.
2. En Railway, PostgreSQL > Backups > PITR, elegir ese instante.
3. Railway crea un servicio restaurado independiente; esperar a que termine replay WAL.
4. No cambiar trafico todavia. Ejecutar todos los pasos de validacion anteriores.
5. Actualizar PgBouncer y `MIGRATION_DATABASE_URL` para el nuevo servicio.
6. Desplegar backend/worker, comprobar `/ready` y desbloquear trafico.
7. Reactivar PITR en el servicio restaurado.

## Ensayo trimestral

Crear un ticket operativo con backup elegido, RPO/RTO medido, checksum, revision, recuentos y resultado. Restaurar en entorno efimero, ejecutar migraciones, RLS, healthchecks y smoke tests, destruir de forma segura el entorno y corregir cualquier desviacion antes de declarar el backup valido.
