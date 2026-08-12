# Despliegue de ForgeOps

## Entornos

ForgeOps utiliza recursos independientes en `local`, `staging` y `production`. No se comparten bases de datos, buckets, Redis, secretos ni cuentas SMTP entre staging y produccion.

| Entorno | Configuracion | Datos demo | Storage |
| --- | --- | --- | --- |
| Local | `.env` desde `.env.example` | Permitidos | Volumen local |
| Demo autohospedada | `.env.demo` | Sin seed automatico | Volumen local |
| Staging Railway | Variables desde `.env.staging.example` | Opcionales y controlados | Bucket S3 propio |
| Produccion Railway | Variables desde `.env.production.example` | Prohibidos | Bucket S3 propio |

## Local

```powershell
Copy-Item .env.example .env
docker compose up --build -d
docker compose ps
Invoke-WebRequest http://localhost:8000/ready
```

El backend aplica migraciones, prepara el rol PostgreSQL restringido y carga datos demo solo si `SEED_DEMO_DATA=true` y `ALLOW_DEMO_SEED=true`.

## Demo autohospedada

```powershell
Copy-Item .env.demo.example .env.demo
docker compose --env-file .env.demo -f docker-compose.demo.yml config --quiet
docker compose --env-file .env.demo -f docker-compose.demo.yml up --build -d
```

La demo usa Caddy para HTTPS, PostgreSQL, Redis, backend, worker y frontend. No es la topologia recomendada para produccion SaaS porque conserva documentos en un volumen local.

## Staging y produccion

1. Crear los servicios descritos en [railway-production.md](railway-production.md).
2. Cargar variables del ejemplo correspondiente y sustituir marcadores.
3. Configurar el archivo Railway de cada servicio.
4. Crear dominios y validar DNS/HTTPS.
5. Ejecutar la primera migracion desde el pre-deploy del backend.
6. Crear el operador propietario con `python -m scripts.bootstrap_operator`.
7. Verificar `/health`, `/ready`, login cliente, login operador, storage y un job de correo.

## Migraciones

Las migraciones usan `MIGRATION_DATABASE_URL` cuando esta definida. El proceso web utiliza `DATABASE_URL`, que en produccion debe pertenecer a un rol sin `SUPERUSER`, sin `BYPASSRLS` y sin propiedad de tablas.

```bash
alembic current
alembic upgrade head
python -m scripts.check_migrations
alembic check
```

Una migracion de produccion sigue expand/migrate/contract: primero cambios compatibles, despues backfill y aplicacion, y en una release posterior eliminacion de estructuras antiguas. Operaciones destructivas requieren backup validado y revision manual.

## Rollback

El rollback de aplicacion se hace redeplegando el ultimo artefacto compatible. No ejecutar `alembic downgrade` automaticamente. Si la migracion es incompatible, activar `MAINTENANCE_MODE`, restaurar una copia o PITR en un servicio nuevo, validar y cambiar `MIGRATION_DATABASE_URL`/`DATABASE_URL` segun [backup-and-recovery.md](backup-and-recovery.md).
