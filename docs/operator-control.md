# Control propietario de ForgeOps

El backoffice `/control` es el plano de gobierno de la plataforma. No pertenece a ninguna empresa cliente y sus cuentas se almacenan en `platform_operators`.

## Preparacion inicial

```powershell
$env:OPERATOR_BOOTSTRAP_NAME="ForgeOps Owner"
$env:OPERATOR_BOOTSTRAP_EMAIL="owner@example.com"
$env:OPERATOR_BOOTSTRAP_PASSWORD="UnaContrasenaSegura123!"
docker compose exec backend python -m scripts.bootstrap_operator
```

Registra la clave o URI mostrada en Microsoft Authenticator, Google Authenticator, 1Password o una aplicacion TOTP equivalente. La clave solo aparece durante el alta y se guarda cifrada con una clave derivada de `SECRET_KEY`.

## Operacion

- `/control`: indicadores globales, vencimientos y adopcion modular.
- `/control/companies`: cartera, actividad, planes, modulos y ampliaciones.
- `/control/audit`: accesos y cambios del propietario.
- `/control/security`: estado MFA y cambio de contrasena.

Suspender o desactivar exige motivo. Desactivar una empresa revoca sus sesiones renovables. La ampliacion de una prueba conserva fecha anterior, fecha nueva, dias y motivo.

## Frontera de privacidad

El operador ve cantidades agregadas, estado comercial y administradores de contacto. No puede abrir documentos, averias, ordenes ni consultas de IA desde el backoffice. Un futuro modo soporte debe incorporar solicitud del cliente, finalidad, caducidad y auditoria antes de habilitar acceso temporal.

## Seguridad

- MFA TOTP obligatorio y rechazo de codigos reutilizados.
- Bloqueo temporal tras cinco intentos fallidos.
- Access token de 10 minutos y sesion renovable de ocho horas.
- Cookie `HttpOnly`, `SameSite=Strict` y `Secure` en produccion.
- Cambio de contrasena revoca todas las sesiones.
- Rutas y tokens independientes de la autenticacion de clientes.
