# ForgeOps

ForgeOps es una plataforma SaaS B2B multiempresa para mantenimiento industrial. Centraliza plantas, activos, incidencias, ordenes, preventivos, repuestos, documentacion tecnica e inteligencia documental con trazabilidad por usuario.

La version **1.2.3 Production Deployment Foundation** convierte el piloto funcional en una base desplegable, verificable y operable: servicios stateless, aislamiento PostgreSQL RLS, storage S3, Redis/worker, planes y limites, PWA, backoffice propietario, CI/CD y validacion estricta de releases.

## Producto

- Dashboard operativo y preparacion del piloto.
- Activos, criticidad, estado y contexto de planta.
- Incidencias y ordenes con asignacion, prioridad e historial.
- Listados de activos, incidencias y ordenes paginados y filtrados en servidor.
- Preventivos, inventario y movimientos de repuesto.
- Documentos privados, extraccion, pgvector y RAG con fuentes.
- Usuarios y roles por empresa con invitaciones seguras y activacion por el empleado.
- Centro de notificaciones para trabajos asignados y alertas operativas.
- Trial autogestionado de 30 dias y onboarding integrado.
- Planes Demo, Trial, Starter, Pro, Industrial y Enterprise.
- Limites de usuarios, plantas, activos y almacenamiento.
- Backoffice `/control` con identidad independiente, MFA y auditoria.
- PWA instalable y cola local restringida para borradores compatibles.

## Arquitectura

```text
Next.js PWA  ->  FastAPI /api/v1  ->  PostgreSQL + RLS + pgvector
                         |         ->  Redis -> RQ worker
                         |         ->  S3 compatible
                         |         ->  SMTP / Sentry opcional
Platform Control /control --------> agregados y gobierno comercial
```

Frontend, API y worker son contenedores independientes. Las sesiones viven en PostgreSQL; los jobs se persisten cifrados e idempotentes antes de entrar en Redis; los documentos nunca dependen del disco del contenedor en produccion.

## Inicio local

Requisitos: Docker Desktop y Docker Compose.

```powershell
git clone https://github.com/NoePerezBlancoo/Mantenimiento.git forgeops
Set-Location forgeops
Copy-Item .env.example .env
docker compose up --build -d
docker compose ps
```

- Aplicacion: `http://localhost:3000`
- API: `http://localhost:8000/api/v1`
- OpenAPI local: `http://localhost:8000/docs`
- Control propietario: `http://localhost:3000/control/login`
- Health: `http://localhost:8000/health`
- Readiness: `http://localhost:8000/ready`

El entorno local carga una empresa de ejemplo si `SEED_DEMO_DATA=true`. Las credenciales se muestran en la interfaz solo cuando `NEXT_PUBLIC_DEMO_CREDENTIALS=true`.

## Operador ForgeOps

```powershell
$env:OPERATOR_BOOTSTRAP_NAME="ForgeOps Owner"
$env:OPERATOR_BOOTSTRAP_EMAIL="owner@example.com"
$env:OPERATOR_BOOTSTRAP_PASSWORD="UnaContrasenaSegura123!"
docker compose exec backend python -m scripts.bootstrap_operator
```

El comando entrega una vez el secreto/URI TOTP. No se comparte con cuentas de empresa.

## Calidad

```powershell
docker compose exec -T backend ruff check app scripts tests alembic
docker compose exec -T backend pytest
docker compose exec -T backend alembic check
docker compose exec -T backend python -m scripts.check_migrations
docker compose exec -T frontend npm run lint
docker compose exec -T frontend npm run typecheck
docker compose exec -T frontend npm test
docker compose exec -T frontend npm run build
docker compose config --quiet
```

GitHub Actions repite estas comprobaciones con PostgreSQL y Redis reales, prueba ataques tenant/RLS, audita dependencias, busca secretos y construye las imagenes.

## Local AI Development

ForgeOps incluye un orquestador local para delegar tareas acotadas a Aider y modelos Ollama sin dar acceso a `main`, credenciales o infraestructura. Cada tarea utiliza una rama `ai/*`, un worktree independiente, un contenedor aislado, quality gates y revision final de Codex.

- [Instalacion](docs/local-ai/installation.md)
- [Operaciones](docs/local-ai/operations.md)
- [Protocolo Codex](docs/local-ai/codex-orchestration.md)
- [Resolucion de problemas](docs/local-ai/troubleshooting.md)

## Seguridad

- Argon2, JWT corto, refresh rotatorio `HttpOnly` e invitaciones de un solo uso.
- MFA TOTP obligatorio y bloqueo para operadores.
- Autorizacion por rol y proteccion del ultimo administrador.
- Aislamiento por empresa en servicios y PostgreSQL RLS forzado.
- Rol runtime PostgreSQL sin superusuario ni bypass.
- CORS explicito, cookies seguras, headers defensivos y rate limit Redis.
- Archivos por UUID, validacion MIME/firma, bucket privado y URL firmada.
- Errores sin traces con request/correlation ID y logs JSON.
- Recuperacion de errores de interfaz con referencia de soporte.
- Configuracion de produccion fail-fast ante valores inseguros.

## Despliegue

Railway es la plataforma objetivo inicial. El repositorio contiene Config as Code para frontend, backend y worker, ejemplos completos por entorno y una topologia con PgBouncer, PostgreSQL HA, Redis y Bucket.

El despliegue externo requiere crear y financiar la cuenta Railway, configurar dominios/DNS, SMTP, secrets, bucket, backups/PITR y aprobaciones de GitHub. No hay credenciales reales en el repositorio.

Guias principales:

- [Arquitectura](docs/architecture.md)
- [Despliegue](docs/deployment.md)
- [Railway](docs/railway-production.md)
- [Runbook](docs/production-runbook.md)
- [Release](docs/release-process.md)
- [Backup y recovery](docs/backup-and-recovery.md)
- [Multi-tenancy](docs/multi-tenancy-security.md)
- [Seguridad](docs/security.md)
- [Storage](docs/storage.md)
- [PWA](docs/pwa.md)
- [Privacidad](docs/data-privacy-architecture.md)
- [Guia cloud para cliente](docs/customer-cloud-security.md)
- [Decisiones ADR](docs/adr/)

## Estado

Implementado y probado localmente: nucleo operativo, backoffice MFA, planes/limites, RLS, storage abstraction, Redis/worker, password reset, PWA, Docker y tests.

Preparado pero dependiente de configuracion externa: Railway staging/production, dominios publicos, PostgreSQL HA/PgBouncer gestionados, Bucket, SMTP, Sentry y PITR.

Fuera de V1.2.3: facturacion automatica, exportacion/destruccion completa de tenant, antivirus gestionado, OPC UA/MQTT/ERP productivos y SSO Enterprise.

## Licencia

Distribuido bajo licencia MIT. Consulta [LICENSE](LICENSE).
