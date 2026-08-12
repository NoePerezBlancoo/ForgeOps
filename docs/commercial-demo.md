# Demo comercial de 30 dias

ForgeOps permite compartir una unica URL de acceso. Cada evaluador crea su propia empresa, recibe 30 dias de uso y entra directamente en el recorrido de primeros pasos.

## Recorrido del evaluador

1. Abre `/login` y selecciona `Crear prueba de 30 dias`.
2. Indica empresa, planta, responsable y credenciales.
3. Decide si desea datos de ejemplo.
4. Acepta las condiciones de evaluacion.
5. Accede a `/getting-started` y completa el flujo guiado.
6. Activa o desactiva capacidades desde `/modules`.

Los datos de ejemplo incluyen tres activos, una incidencia, dos ordenes, un preventivo y dos repuestos. Se crean dentro de la empresa registrada y no se mezclan con MetalWorks ni con otras pruebas.

## Ciclo de acceso

- `TRIAL`: lectura y escritura hasta `trial_ends_at`.
- `EXPIRED`: datos conservados y acceso operativo bloqueado.
- `ACTIVE`: acceso profesional sin caducidad de prueba.
- `SUSPENDED`: cuenta detenida por el operador.

El vencimiento se calcula en tiempo real, por lo que no depende de una tarea programada. Las escrituras vencidas devuelven HTTP 402; seguridad y cierre de sesiones siguen disponibles. La API conserva lectura autenticada para una exportacion controlada por el operador.

## Operacion comercial

Ampliar una evaluacion:

```bash
docker compose exec backend python -m scripts.manage_subscription \
  --email owner@example.com --extend-trial 15
```

Activar continuidad:

```bash
docker compose exec backend python -m scripts.manage_subscription \
  --email owner@example.com --plan PROFESSIONAL --status ACTIVE
```

Suspender:

```bash
docker compose exec backend python -m scripts.manage_subscription \
  --email owner@example.com --status SUSPENDED
```

## Publicacion

Para enviar la demo a terceros se necesita un despliegue HTTPS estable con PostgreSQL y volumen documental persistentes. Configura un dominio para el frontend y otro para la API, copias de seguridad, monitorizacion y limitacion de peticiones en el proxy.

El texto de `/legal` es una base funcional para demostracion, no una politica juridica definitiva. Antes de una oferta publica debe sustituirse por los datos del titular, privacidad, retencion, soporte y condiciones comerciales revisadas.

### Despliegue en un VPS

El repositorio incluye `docker-compose.demo.yml` y `deploy/Caddyfile`. Publican frontend y API bajo un unico dominio, solicitan TLS automaticamente y no exponen PostgreSQL.

```bash
cp .env.demo.example .env.demo
# Editar dominio, contrasena, clave y correo comercial
docker compose --env-file .env.demo -f docker-compose.demo.yml up -d --build
docker compose --env-file .env.demo -f docker-compose.demo.yml ps
curl --fail https://demo.example.com/health
```

El dominio debe apuntar previamente a la IP publica del servidor y los puertos 80/443 deben estar abiertos. Los datos quedan en volumenes persistentes de PostgreSQL, documentos y certificados.
