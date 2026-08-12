# Despliegue de piloto

Esta guia define el minimo operativo para desplegar ForgeOps V1.0 en una empresa piloto. No sustituye las politicas de infraestructura del cliente.

## Requisitos

- Servidor Linux o Windows con Docker Compose actualizado.
- DNS y certificado TLS gestionados por un proxy inverso.
- Volumen persistente para PostgreSQL y documentos.
- Copia de seguridad externa con retencion definida.
- Acceso administrativo restringido por VPN o red corporativa cuando sea posible.

## Variables obligatorias

```dotenv
APP_ENV=production
SEED_DEMO_DATA=false
POSTGRES_DB=forgeops
POSTGRES_USER=forgeops
POSTGRES_PASSWORD=replace-with-a-long-random-password
SECRET_KEY=replace-with-at-least-32-random-characters
FRONTEND_URL=https://forgeops.example.com
NEXT_PUBLIC_API_URL=https://forgeops-api.example.com/api/v1
COOKIE_SECURE=true
TRIAL_DAYS=30
TRIAL_SIGNUP_ENABLED=true
```

No reutilices las credenciales demo. `APP_ENV=production` impide arrancar con la clave de desarrollo, cookies inseguras o una URL local.

Desactiva `TRIAL_SIGNUP_ENABLED` en instalaciones privadas donde las empresas solo deban crearse mediante bootstrap. En una demo publica, aplica tambien limitacion de peticiones en el proxy inverso sobre `/api/v1/auth/register-trial`.

## Red

- Publica frontend y API exclusivamente a traves del proxy TLS.
- No expongas el puerto `5432` a Internet.
- Restringe Swagger si la politica del cliente no permite documentacion publica.
- Configura los origenes permitidos con `FRONTEND_URL`.

## Datos y copias

Elementos que deben respaldarse conjuntamente:

- Base PostgreSQL `forgeops`.
- Volumen `forgeops_uploads`.
- Variables y secretos del despliegue.

Ejemplo de copia logica:

```bash
docker compose exec -T postgres pg_dump -U forgeops -Fc forgeops > forgeops.dump
```

La restauracion debe probarse antes del piloto y despues de cambios relevantes. Conserva las copias fuera del servidor de aplicacion y cifra el soporte de destino.

## Puesta en marcha

```bash
docker compose up -d --build
docker compose ps
curl --fail https://forgeops-api.example.com/health
curl --fail https://forgeops-api.example.com/ready
```

Crea la empresa y el primer administrador sin activar datos demo:

```bash
docker compose exec \
  -e BOOTSTRAP_COMPANY_NAME="Industrial Pilot S.L." \
  -e BOOTSTRAP_COMPANY_TAX_ID="B00000000" \
  -e BOOTSTRAP_ADMIN_NAME="Administrador" \
  -e BOOTSTRAP_ADMIN_EMAIL="admin@example.com" \
  -e BOOTSTRAP_ADMIN_PASSWORD="ReplaceThis123!" \
  -e BOOTSTRAP_PLANT_NAME="Planta principal" \
  -e BOOTSTRAP_PLANT_CODE="PLT-01" \
  backend python -m scripts.bootstrap_admin
```

El comando es idempotente: no duplica la empresa, el usuario ni la planta. No restablece una contrasena existente.

Despues del primer acceso:

1. Cambia la contrasena del administrador demo o crea el administrador real.
2. Completa la ficha de empresa y revisa zona horaria y prefijo.
3. Configura plantas, usuarios y roles.
4. Revisa el indicador de preparacion para piloto.
5. Desactiva cuentas que no participen en la implantacion.
6. Verifica la descarga documental y el plan de copias.
7. Revisa modulos activos, tutorial y politica de vencimiento de pruebas.

## Operacion

- Revisa `/health` y `/ready` desde el monitor externo.
- Centraliza los logs de contenedores y conserva `X-Request-ID` para diagnostico.
- Revisa la auditoria administrativa y las sesiones activas.
- Crea el operador propietario con `scripts.bootstrap_operator`, registra su MFA y conserva la clave TOTP en un gestor seguro.
- Verifica que `/control` solo sea accesible por HTTPS y que la cuenta de operador no se comparta.
- Ejecuta migraciones solo como parte de una version respaldada.
- Actualiza dependencias mediante una rama y CI, nunca directamente en produccion.

## IA opcional

El piloto funciona con `AI_PROVIDER=local`. Si se habilita OpenAI, la empresa debe aprobar el tratamiento de la documentacion y la clave debe permanecer en el entorno del backend. Reindexa los documentos despues de cambiar el proveedor.

## Recuperacion

Ante una incidencia grave:

1. Deten los servicios de escritura.
2. Conserva logs, version desplegada y copia de los volumenes afectados.
3. Restaura PostgreSQL y documentos desde el mismo punto temporal.
4. Ejecuta `alembic current` y comprueba `/ready`.
5. Valida login, activos, una descarga y una consulta documental antes de reabrir.
