# ForgeOps

ForgeOps es una plataforma SaaS B2B para digitalizar el mantenimiento de pequenas y medianas empresas industriales. Centraliza activos, incidencias, ordenes de trabajo, preventivos, repuestos, documentacion tecnica y conocimiento operativo con aislamiento multiempresa.

La V0.3 es una aplicacion funcional preparada para demostraciones y evolucion hacia un piloto. Incluye API REST, autenticacion segura, permisos por rol, migraciones, datos demo idempotentes, almacenamiento documental privado, asistente con citas verificables, interfaz responsive y pruebas automatizadas.

## Funcionalidad

- Login con access token JWT y refresh token rotatorio en cookie `HttpOnly`.
- Aislamiento logico por empresa mediante `company_id`.
- Roles `SUPER_ADMIN`, `ADMIN`, `MAINTENANCE_MANAGER`, `TECHNICIAN` y `VIEWER`.
- Empresas, plantas, usuarios y activos industriales.
- Incidencias con prioridad, responsable, parada, causa raiz y resolucion.
- Ordenes correctivas, preventivas, de inspeccion y mejora.
- Planes preventivos recurrentes con generacion controlada de ordenes.
- Inventario de repuestos con stock minimo y movimientos inmutables.
- Documentos privados vinculados a activos, versionados e indexables.
- Extraccion real de TXT, PDF y DOCX con fragmentacion controlada.
- Recuperacion local operativa sin servicios externos.
- Busqueda vectorial con `pgvector` y respuestas OpenAI opcionales.
- Asistente documental con filtro por activo, citas, descarga de fuentes e historial.
- Dashboard con disponibilidad, carga, paradas, preventivos y alertas de stock.
- Swagger/OpenAPI, Alembic, semilla demo y GitHub Actions.

## Stack

```text
Frontend    Next.js 16, React 19, TypeScript, Tailwind CSS
Backend     FastAPI, SQLAlchemy 2, Pydantic 2, Alembic
Datos       PostgreSQL 17, pgvector
IA opcional OpenAI Responses API, text-embedding-3-small
Ejecucion   Docker Compose
```

El backend es un monolito modular. Cada dominio mantiene sus modelos, esquemas, servicios y rutas. Consulta [docs/architecture.md](docs/architecture.md) y [docs/document-intelligence.md](docs/document-intelligence.md) para conocer las decisiones principales.

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

El backend aplica las migraciones y prepara los datos demo automaticamente. La semilla puede ejecutarse repetidamente sin duplicar registros ni fragmentos documentales.

## Credenciales demo

```text
Email:    admin@metalworks-demo.local
Password: Admin123!
Rol:      ADMIN
```

Estas credenciales solo deben utilizarse para desarrollo y demostracion.

## Inteligencia documental

La configuracion predeterminada es `AI_PROVIDER=local`. Indexa los documentos y responde de forma extractiva con referencias, sin enviar informacion a terceros ni requerir una clave.

Para habilitar embeddings y respuestas generativas, configura estas variables solo en el servidor:

```dotenv
AI_PROVIDER=openai
OPENAI_API_KEY=replace-with-a-server-side-key
OPENAI_CHAT_MODEL=gpt-5
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
```

Tras cambiar de proveedor, reconstruye el backend y usa `Reindexar` en la base documental para generar los embeddings de los documentos existentes.

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

## API V0.3

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

GET  /api/v1/ai/status
GET  /api/v1/ai/history
POST /api/v1/ai/query
POST /api/v1/ai/documents/index
POST /api/v1/ai/documents/{id}/index
```

## Calidad

La suite cubre autenticacion, permisos, aislamiento entre empresas, activos, incidencias, ordenes, preventivos sin duplicados, stock no negativo, privacidad documental, extraccion, fragmentacion, indexacion idempotente y respuestas con fuentes. El workflow ejecuta lint, pruebas, typecheck y build en cada `push` y `pull request`.

## Hoja de ruta

- **V0.1:** activos, incidencias, ordenes de trabajo y dashboard. Completada.
- **V0.2:** preventivos, inventario, movimientos y documentos tecnicos. Completada.
- **V0.3:** ingesta documental, embeddings y RAG con fuentes verificables. Completada.
- **V0.4:** adaptadores OPC UA, MQTT, Modbus TCP, ERP y bases externas.
- **V1.0:** auditoria avanzada, observabilidad, backups, almacenamiento cloud y piloto real.

## Licencia

Distribuido bajo licencia MIT. Consulta [LICENSE](LICENSE).
