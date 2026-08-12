# ForgeOps

ForgeOps es una plataforma SaaS B2B para digitalizar la gestión de mantenimiento en pequeñas y medianas empresas industriales. Centraliza activos, incidencias, órdenes de trabajo y KPIs operativos con aislamiento multiempresa y una experiencia diseñada para responsables de mantenimiento y técnicos de planta.

La V0.1 es un MVP funcional: no es un ERP ni una maqueta estática. Incluye API REST, autenticación segura, permisos, base de datos migrada, datos de demostración idempotentes, interfaz operativa y pruebas automatizadas.

## Funcionalidad disponible

- Login con access token JWT y refresh token rotatorio en cookie `HttpOnly`.
- Aislamiento lógico por empresa mediante `company_id`.
- Roles `SUPER_ADMIN`, `ADMIN`, `MAINTENANCE_MANAGER`, `TECHNICIAN` y `VIEWER`.
- Catálogo de empresas, plantas y usuarios para el contexto autenticado.
- Gestión de activos con estado, criticidad, ubicación y datos técnicos.
- Registro y seguimiento de incidencias, responsables, parada, causa raíz y resolución.
- Creación y ejecución de órdenes de trabajo correctivas, preventivas, de inspección y mejora.
- Dashboard con disponibilidad, carga de trabajo, incidencias críticas y horas de parada.
- Swagger/OpenAPI, migraciones Alembic, carga demo y pruebas de seguridad funcional.
- Interfaz responsive para escritorio y tablet.

## Arquitectura

```text
industrial-maintenance-ai-saas/
├── backend/        FastAPI, SQLAlchemy, Pydantic y Alembic
├── frontend/       Next.js, React, TypeScript y Tailwind CSS
├── docker/         Notas de infraestructura
├── docs/           Decisiones de arquitectura
└── docker-compose.yml
```

El backend es un monolito modular. Cada dominio mantiene modelos, esquemas, servicios y rutas independientes. Los directorios `ai` e `integrations` contienen únicamente contratos de extensión; no simulan IA ni conexiones industriales inexistentes.

Consulta [docs/architecture.md](docs/architecture.md) para las decisiones principales.

## Requisitos

- Docker Desktop con Docker Compose.
- Puertos locales libres: `3000`, `8000` y `5432`.

No es necesario instalar Python, Node.js ni PostgreSQL en el equipo anfitrión.

## Puesta en marcha

1. Crea el archivo de entorno local:

```powershell
Copy-Item .env.example .env
```

2. Sustituye `POSTGRES_PASSWORD` y `SECRET_KEY` en `.env` antes de exponer el sistema fuera del equipo local.

3. Construye y arranca todos los servicios:

```powershell
docker compose up --build
```

4. Abre los servicios:

- Aplicación: http://localhost:3000
- API: http://localhost:8000
- Swagger: http://localhost:8000/docs
- OpenAPI: http://localhost:8000/api/v1/openapi.json

El backend aplica las migraciones y prepara los datos demo automáticamente. La carga puede repetirse sin duplicar activos, incidencias ni órdenes.

## Credenciales demo

```text
Email:    admin@metalworks-demo.local
Password: Admin123!
Rol:      ADMIN
```

Estas credenciales son públicas y solo sirven para desarrollo y demostración.

## Comandos habituales

```powershell
docker compose up -d --build
docker compose logs -f
docker compose exec backend alembic upgrade head
docker compose exec backend python -m scripts.seed_demo
docker compose exec backend pytest
docker compose exec backend ruff check app scripts tests alembic
docker compose exec frontend npm run lint
docker compose exec frontend npm run typecheck
docker compose down
```

Para eliminar también los datos locales de PostgreSQL:

```powershell
docker compose down -v
```

## API V0.1

```text
POST  /api/v1/auth/login
POST  /api/v1/auth/refresh
POST  /api/v1/auth/logout
GET   /api/v1/auth/me
GET   /api/v1/companies/current
GET   /api/v1/plants
GET   /api/v1/users
GET   /api/v1/assets
POST  /api/v1/assets
PATCH /api/v1/assets/{id}
GET   /api/v1/incidents
POST  /api/v1/incidents
PATCH /api/v1/incidents/{id}
GET   /api/v1/work-orders
POST  /api/v1/work-orders
PATCH /api/v1/work-orders/{id}
GET   /api/v1/dashboard
```

## Pruebas

La suite cubre:

- autenticación correcta e incorrecta;
- denegación de escritura al rol de consulta;
- aislamiento de activos entre dos empresas;
- creación de activos;
- creación y asignación de incidencias;
- creación y asignación de órdenes de trabajo.

El workflow de GitHub Actions ejecuta lint, pruebas, typecheck y build en cada `push` o `pull request`.

## Hoja de ruta

- **V0.1:** activos, incidencias, órdenes de trabajo y dashboard.
- **V0.2:** preventivos, inventario, consumos y documentos técnicos.
- **V0.3:** ingesta documental, embeddings y RAG con fuentes verificables.
- **V0.4:** adaptadores OPC UA, MQTT, Modbus TCP, ERP y bases externas.
- **V1.0:** auditoría, observabilidad, backups, almacenamiento cloud y piloto real.

## Licencia

Distribuido bajo licencia MIT. Consulta [LICENSE](LICENSE).

