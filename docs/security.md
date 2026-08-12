# Seguridad de ForgeOps

## Identidad

Las contrasenas usan Argon2 y politica minima. Los access tokens son cortos; los refresh tokens rotan, se guardan como hash en PostgreSQL, viajan en cookie `HttpOnly` y se revocan al cambiar contrasena o desactivar una cuenta. El backoffice utiliza identidad independiente, MFA TOTP obligatorio, anti-replay, bloqueo temporal y auditoria global.

Roles cliente: `SUPER_ADMIN`, `ADMIN`, `MAINTENANCE_MANAGER`, `TECHNICIAN` y `VIEWER`. Las operaciones sensibles protegen el ultimo administrador activo.

## Controles HTTP

- CORS explicito por entorno, sin wildcard en produccion.
- Cookies `Secure`, `HttpOnly` y `SameSite` configurable.
- HSTS, anti-frame, nosniff, referrer y permissions policy.
- Rate limit Redis para login, trial, reset y uploads.
- Errores estandar sin trace y con `request_id`/`correlation_id`.
- Swagger configurable mediante `DOCS_ENABLED`.

## Archivos

Extensiones, MIME y magic bytes se validan antes de guardar. Las claves son UUID con prefijo de empresa y activo. El bucket es privado y las descargas usan autorizacion tenant y URL firmada breve. Office/PDF no se ejecutan; la extraccion documental ocurre en worker.

Un antivirus/escaneo de contenido es un control externo recomendado antes de abrir el piloto a uploads no confiables. Hasta integrarlo, limitar formatos, tamano y usuarios con permiso de carga.

## Secretos

Secretos solo en Railway/GitHub environments: JWT, DB, Redis, S3, SMTP, IA, Sentry y TOTP cifrado. Nunca en variables `NEXT_PUBLIC_*`, logs, incidencias ni Git. Gitleaks y auditorias de dependencias se ejecutan en CI.

Rotacion:

1. Crear credencial nueva en proveedor.
2. Actualizar staging y verificar.
3. Actualizar produccion con solapamiento cuando sea posible.
4. Revocar credencial antigua.
5. Registrar hora, alcance y responsable sin registrar el secreto.

Rotar `SECRET_KEY` invalida tokens y cambia la clave derivada para payloads cifrados pendientes; drenar o reprocesar la cola antes.

## Soporte

V1.2.1 no incluye impersonacion. El operador solo ve metadatos agregados y controles comerciales. Un futuro modo soporte debe exigir solicitud del cliente, motivo, caducidad, minimo privilegio, aviso visible y auditoria completa.
