# ForgeOps 1.2.1 - Production Foundation

## Implementado

- Identidad de operador independiente con MFA TOTP, sesiones y auditoria.
- Planes, modulos, feature overrides y limites con consumo real.
- PostgreSQL RLS forzado y prueba de ataque entre tenants.
- Runtime stateless con PostgreSQL/PgBouncer, Redis y worker RQ.
- Jobs durables, cifrados, idempotentes y correo transaccional.
- Password reset de un solo uso y revocacion de sesiones.
- Storage local/S3, bucket privado, firmas y validacion de archivos.
- PWA con manifest, iconos, service worker y cola IndexedDB restringida.
- Health/readiness, logs JSON, correlation IDs y Sentry opcional.
- Paginacion tenant-safe para activos, incidencias y ordenes, con filtros en servidor.
- Error boundary de interfaz con recuperacion y referencia de soporte.
- Entornos local/demo/staging/production, Docker y Railway Config as Code.
- CI de backend/frontend/RLS/seguridad/contenedores y release protegido.
- Runbooks, backup/recovery, privacidad, cliente y nueve ADRs.

## Compatibilidad

La API se mantiene en `/api/v1`. Las migraciones llegan hasta `f72c84da3105`. `CompanyPlan.PROFESSIONAL` se conserva como valor legacy mientras los planes nuevos se adoptan.

## Configuracion requerida

Produccion exige PostgreSQL, rol runtime restringido, Redis, S3, SMTP, cookies HTTPS y URLs no locales. El arranque rechaza configuracion insegura. Railway y los proveedores externos deben configurarse antes de un piloto publico.

## Riesgos conocidos

- La sincronizacion automatica de cada formulario offline se habilitara tras definir sus contratos de conflicto.
- Antivirus y textos legales definitivos son controles externos pendientes.
- Exportacion y destruccion completa de tenant estan disenadas, no implementadas.
