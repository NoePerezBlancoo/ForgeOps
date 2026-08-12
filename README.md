# ForgeOps

ForgeOps es una plataforma SaaS B2B para digitalizar el mantenimiento de pequenas y medianas empresas industriales. Sustituye hojas de calculo, papel y conversaciones dispersas por una operacion trazable sobre plantas, activos, incidencias, ordenes, preventivos, repuestos y documentacion tecnica.

La V1.1 esta preparada para demostraciones comerciales autogestionadas y pilotos controlados. Cada evaluador puede crear un entorno privado durante 30 dias, seguir un tutorial integrado y activar solo los modulos que necesita su empresa.

## Capacidades V1.1

- Alta autogestionada de pruebas de 30 dias, con espacio multiempresa aislado.
- Datos de ejemplo opcionales para empezar a evaluar el producto inmediatamente.
- Caducidad calculada en tiempo real y bloqueo de escritura al finalizar la prueba.
- Gestion operativa de ampliacion, activacion o suspension de suscripciones.
- Centro de primeros pasos con progreso automatico y tutorial de flujo completo.
- Ayuda contextual siempre disponible desde la aplicacion.
- Nucleo operativo estable y modulos opcionales por empresa.

- Autenticacion JWT con access token corto y refresh token rotatorio en cookie `HttpOnly`.
- Roles `SUPER_ADMIN`, `ADMIN`, `MAINTENANCE_MANAGER`, `TECHNICIAN` y `VIEWER`.
- Aislamiento logico por empresa en todos los datos operativos y documentales.
- Perfil de empresa, zona horaria, formato regional y prefijo configurable de ordenes.
- Plantas administrables y selector global que filtra la operacion real.
- Usuarios, puestos, roles, activacion, restablecimiento de contrasena y cierre de sesiones.
- Registro de auditoria para accesos y cambios administrativos.
- Indicador de preparacion para piloto y accesos directos a pasos pendientes.
- Activos industriales con criticidad, ubicacion, fabricante y estado.
- Incidencias con prioridad, responsable, tiempos de parada, causa y resolucion.
- Ordenes correctivas, preventivas, de inspeccion y mejora.
- Preventivos recurrentes con generacion idempotente de ordenes.
- Inventario con stock minimo y movimientos inmutables.
- Documentos privados vinculados a activos con extraccion TXT, PDF y DOCX.
- Asistente documental local o RAG OpenAI opcional, siempre con fuentes descargables.
- Dashboard operativo con disponibilidad, carga, paradas y alertas.
- API OpenAPI, migraciones Alembic, datos demo idempotentes y CI.

## Stack

```text
Frontend    Next.js 16, React 19, TypeScript, Tailwind CSS
Backend     FastAPI, SQLAlchemy 2, Pydantic 2, Alembic
Datos       PostgreSQL 17, pgvector
IA opcional OpenAI Responses API, text-embedding-3-small
Ejecucion   Docker Compose
```

ForgeOps mantiene un monolito modular deliberado. Consulta [Arquitectura](docs/architecture.md), [Inteligencia documental](docs/document-intelligence.md), [Demo comercial](docs/commercial-demo.md) y [Despliegue de piloto](docs/pilot-deployment.md).

Para una demo publica de un solo dominio se incluye `docker-compose.demo.yml`, con HTTPS automatico mediante Caddy, PostgreSQL privado y persistencia documental.

## Inicio rapido

Requisitos: Docker Desktop y los puertos `3000`, `8000` y `5432` disponibles.

```powershell
Copy-Item .env.example .env
docker compose up -d --build
```

- Aplicacion: http://localhost:3000
- Swagger: http://localhost:8000/docs
- Healthcheck: http://localhost:8000/health
- Readiness: http://localhost:8000/ready

El backend aplica migraciones y carga datos demo automaticamente. La semilla se puede ejecutar repetidamente sin duplicar registros ni fragmentos documentales.

Desde la pantalla de acceso se puede crear una empresa de prueba. El registro abre directamente `/getting-started`, prepara una planta y, si se solicita, incorpora datos de ejemplo aislados.

En produccion usa `SEED_DEMO_DATA=false` y crea el primer acceso con `python -m scripts.bootstrap_admin`, tal como se documenta en la guia de despliegue.

## Acceso demo

```text
Email:    admin@metalworks-demo.local
Password: Admin123!
Rol:      ADMIN
```

Estas credenciales solo son validas para desarrollo y demostracion.

## Inteligencia documental

`AI_PROVIDER=local` es el modo predeterminado. No necesita claves externas y responde de forma extractiva con citas. Para activar embeddings y generacion:

```dotenv
AI_PROVIDER=openai
OPENAI_API_KEY=replace-with-a-server-side-key
OPENAI_CHAT_MODEL=gpt-5
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
```

La clave permanece en el backend. Tras cambiar de proveedor se deben reindexar los documentos desde el panel de inteligencia.

## Comandos

```powershell
docker compose up -d --build
docker compose ps
docker compose logs -f
docker compose exec backend alembic upgrade head
docker compose exec backend python -m scripts.seed_demo
docker compose exec backend pytest
docker compose exec backend ruff check app scripts tests alembic
docker compose exec frontend npm run lint
docker compose exec frontend npm run typecheck
docker compose down
```

Reinicio completo de datos locales:

```powershell
docker compose down -v
```

## API principal

```text
/api/v1/auth                    autenticacion, contrasena y sesiones
/api/v1/auth/register-trial     alta publica de prueba
/api/v1/companies               empresa actual y configuracion
/api/v1/plants                  plantas y estado
/api/v1/users                   equipo, roles y credenciales
/api/v1/audit-events            trazabilidad administrativa
/api/v1/assets                  activos industriales
/api/v1/incidents               incidencias
/api/v1/work-orders             ordenes de trabajo
/api/v1/preventive-maintenance  planes preventivos
/api/v1/inventory               repuestos y movimientos
/api/v1/documents               archivos tecnicos privados
/api/v1/ai                      indexacion y consultas documentales
/api/v1/dashboard               KPIs y preparacion del piloto
/api/v1/onboarding              progreso y tutorial integrado
```

## Seguridad

- Hash Argon2 para contrasenas y politica minima de complejidad.
- Refresh tokens almacenados como hash y revocables.
- Sesiones cerradas al cambiar contrasena o desactivar un usuario.
- Proteccion del ultimo administrador activo.
- Descargas autenticadas y almacenamiento fuera del directorio publico.
- Cabeceras defensivas, CORS explicito y validacion estricta en produccion.
- Claves y secretos excluidos del repositorio.

`APP_ENV=production` exige una clave distinta de la predeterminada, cookies seguras y un `FRONTEND_URL` no local. Consulta la guia de despliegue antes de exponer un piloto.

## Calidad

La suite cubre autenticacion, permisos, multiempresa, operaciones de mantenimiento, inventario, documentos, RAG, administracion, ultimo administrador, revocacion de sesiones, auditoria, filtros de planta, extraccion e idempotencia. GitHub Actions ejecuta Ruff, Pytest, ESLint, TypeScript y la build de Next.js en cada cambio.

## Gestion de pruebas

Ampliar una prueba:

```powershell
docker compose exec backend python -m scripts.manage_subscription --email owner@example.com --extend-trial 15
```

Convertirla a plan profesional:

```powershell
docker compose exec backend python -m scripts.manage_subscription --email owner@example.com --plan PROFESSIONAL --status ACTIVE
```

## Alcance del piloto

V1.1 incorpora aprovisionamiento automatizado de empresas y ciclo de prueba. Para explotacion SaaS publica todavia deben integrarse facturacion, correo transaccional, almacenamiento cloud, monitorizacion centralizada y los textos legales definitivos del titular.

## Hoja de ruta

- **V0.1:** activos, incidencias, ordenes y dashboard. Completada.
- **V0.2:** preventivos, inventario y documentos. Completada.
- **V0.3:** ingesta documental y RAG verificable. Completada.
- **V1.0:** administracion, seguridad, auditoria, contexto de planta y piloto comercial. Completada.
- **V1.1:** prueba de 30 dias, onboarding guiado y configuracion modular. Completada.
- **Siguiente:** facturacion, correo transaccional, OPC UA, MQTT, ERP y observabilidad cloud.

## Licencia

Distribuido bajo licencia MIT. Consulta [LICENSE](LICENSE).
