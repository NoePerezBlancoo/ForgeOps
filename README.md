# ForgeOps

ForgeOps es una plataforma SaaS B2B para digitalizar el mantenimiento de pequenas y medianas empresas industriales. Centraliza activos, incidencias, ordenes de trabajo, mantenimiento preventivo, repuestos, documentacion tecnica y KPIs operativos con aislamiento multiempresa.

La V0.2 es una aplicacion funcional, no una maqueta estatica. Incluye API REST, autenticacion segura, permisos por rol, migraciones, datos demo idempotentes, almacenamiento documental privado, interfaz responsive y pruebas automatizadas.

## Funcionalidad

- Login con access token JWT y refresh token rotatorio en cookie `HttpOnly`.
- Aislamiento logico por empresa mediante `company_id`.
- Roles `SUPER_ADMIN`, `ADMIN`, `MAINTENANCE_MANAGER`, `TECHNICIAN` y `VIEWER`.
- Empresas, plantas, usuarios y activos industriales.
- Incidencias con prioridad, responsable, parada, causa raiz y resolucion.
- Ordenes correctivas, preventivas, de inspeccion y mejora.
- Planes preventivos recurrentes con generacion controlada de ordenes.
- Inventario de repuestos con stock minimo y movimientos inmutables.
- Documentos tecnicos privados vinculados a activos y descarga autenticada.
- Dashboard con disponibilidad, carga, paradas, preventivos y alertas de stock.
- Swagger/OpenAPI, Alembic, semilla demo y GitHub Actions.

## Stack

```text
Frontend    Next.js 16, React 19, TypeScript, Tailwind CSS
Backend     FastAPI, SQLAlchemy 2, Pydantic 2, Alembic
Datos       PostgreSQL 17
Ejecucion   Docker Compose
```

El backend es un monolito modular. Cada dominio mantiene sus modelos, esquemas, servicios y rutas. Los modulos `ai` e `integrations` contienen contratos de extension y no simulan capacidades todavia inexistentes.

Consulta [docs/architecture.md](docs/architecture.md) para las decisiones principales.

## Puesta en marcha

Requisitos: Docker Desktop y los puertos `3000`, `8000` y `5432` disponibles.

```powershell
Copy-Item .env.example .env
docker compose up -d --build
```

Servicios:

- Aplicacion: http://localhost:3000
- API: http://localhost:8000
- Swagger: http://localhost:8000/docs
- OpenAPI: http://localhost:8000/api/v1/openapi.json

El backend aplica las migraciones y prepara los datos demo automaticamente. La semilla puede ejecutarse repetidamente sin duplicar registros.

## Credenciales demo

```text
Email:    admin@metalworks-demo.local
Password: Admin123!
Rol:      ADMIN
```

Estas credenciales solo deben utilizarse para desarrollo y demostracion.

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

Para reiniciar tambien los datos locales:

```powershell
docker compose down -v
```

## API V0.2

```text
POST  /api/v1/auth/login
POST  /api/v1/auth/refresh
POST  /api/v1/auth/logout
GET   /api/v1/auth/me

GET   /api/v1/assets
GET   /api/v1/incidents
GET   /api/v1/work-orders
GET   /api/v1/dashboard

GET   /api/v1/preventive-maintenance
POST  /api/v1/preventive-maintenance
PATCH /api/v1/preventive-maintenance/{id}
POST  /api/v1/preventive-maintenance/{id}/generate-work-order
POST  /api/v1/preventive-maintenance/actions/generate-due

GET   /api/v1/inventory
POST  /api/v1/inventory
PATCH /api/v1/inventory/{id}
GET   /api/v1/inventory/{id}/movements
POST  /api/v1/inventory/{id}/movements

GET    /api/v1/documents
POST   /api/v1/documents
GET    /api/v1/documents/{id}/download
PATCH  /api/v1/documents/{id}
DELETE /api/v1/documents/{id}
```

## Calidad

La suite cubre autenticacion, permisos, aislamiento entre empresas, activos, incidencias, ordenes, preventivos sin duplicar ordenes pendientes, stock no negativo y privacidad documental. El workflow ejecuta lint, pruebas, typecheck y build en cada `push` y `pull request`.

## Hoja de ruta

- **V0.1:** activos, incidencias, ordenes de trabajo y dashboard. Completada.
- **V0.2:** preventivos, inventario, movimientos y documentos tecnicos. Completada.
- **V0.3:** ingesta documental, embeddings y RAG con fuentes verificables.
- **V0.4:** adaptadores OPC UA, MQTT, Modbus TCP, ERP y bases externas.
- **V1.0:** auditoria, observabilidad, backups, almacenamiento cloud y piloto real.

## Licencia

Distribuido bajo licencia MIT. Consulta [LICENSE](LICENSE).
