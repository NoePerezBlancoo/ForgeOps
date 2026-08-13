# ADR-011: Invitaciones seguras y notificaciones tenant-safe

## Estado

Aceptada e implementada el 2026-08-13.

## Contexto

Un administrador no debe conocer ni distribuir contrasenas temporales. El alta tiene que reservar una plaza del plan, conservar la trazabilidad historica y permitir que el empleado establezca su propia credencial. Los avisos operativos deben quedar aislados por empresa y destinatario.

## Decision

- La invitacion almacena solo el resumen SHA-256 del token. El enlace viaja dentro del payload cifrado del job de correo.
- El token es aleatorio, de un solo uso, expira y puede revocarse o rotarse mediante reenvio.
- Las invitaciones pendientes cuentan para el limite de usuarios. La aceptacion vuelve a comprobar la plaza bajo bloqueo de empresa.
- Aceptar crea el usuario y registra invitacion, auditoria y credencial en una transaccion.
- Las invitaciones se conservan; las referencias a usuarios usan `SET NULL` para mantener significado historico.
- PostgreSQL RLS permite al tenant administrar sus invitaciones. El contexto interno `auth` solo puede leer y aceptar una invitacion validada por token.
- Las notificaciones incluyen empresa y destinatario, admiten deduplicacion opcional y solo permiten lectura/acuse dentro del tenant autenticado.
- La primera integracion de dominio cubre asignaciones de OT e incidencias criticas. Preventivos, stock y trial reutilizaran el mismo servicio.

## Consecuencias

El frontend deja de solicitar contrasenas al administrador. SMTP puede configurarse sin cambiar el dominio; en desarrollo, el job y el backend de correo local permiten validar el flujo. El enlace sin credenciales SMTP reales sigue siendo un bloqueo de despliegue, no de arquitectura.

## Verificacion

- Suite funcional de invitacion, expiracion, uso unico, permisos y limites.
- Suite de destinatario, lectura y aislamiento de notificaciones.
- RLS sobre PostgreSQL con rol runtime restringido.
- Migracion `upgrade/downgrade/upgrade` y `alembic check` sin diferencias.
- Build y QA visual en escritorio y movil.
