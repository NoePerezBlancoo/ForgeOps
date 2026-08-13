# ForgeOps Commercial Release 1.0

## Objetivo

Llevar ForgeOps desde la foundation actual hasta un release candidate comercial verificable para pilotos industriales reales. Cada capacidad usa exclusivamente estos estados:

- `IMPLEMENTED`: integrada en codigo y revisada.
- `TESTED`: validada por pruebas automatizadas ejecutadas.
- `STAGING_VALIDATED`: comprobada contra Railway staging real.
- `PRODUCTION_VALIDATED`: comprobada en produccion despues de un cutover autorizado.
- `EXTERNAL_BLOCKER`: requiere una cuenta, secreto, compra o decision del propietario.
- `DEFERRED`: queda fuera del release por una decision explicita.

## Baseline verificada

Fecha de auditoria: 2026-08-13.

| Capacidad | Estado | Evidencia |
| --- | --- | --- |
| Local AI Orchestrator V1.0.1 | `TESTED` | PR #8 fusionado; Quality Gate de `main` verde en cinco jobs |
| SaaS multiempresa y roles | `TESTED` | Filtros tenant, PostgreSQL RLS y pruebas de aislamiento |
| PostgreSQL, PgBouncer y rol runtime | `TESTED` | Migraciones y validaciones de configuracion incluidas en CI |
| Redis y worker durable | `TESTED` | Jobs idempotentes, payload cifrado e integracion de worker |
| Storage privado S3 | `TESTED` | Validacion de firma, claves por tenant y URLs firmadas |
| Trial, onboarding y backoffice | `TESTED` | Flujos API y panel `/control` existentes |
| PWA basica | `IMPLEMENTED` | Manifest, service worker, shell offline y cola local |
| Railway staging automatico | `EXTERNAL_BLOCKER` | Variable GitHub `RAILWAY_STAGING_ENABLED=false` |
| Dominios finales | `EXTERNAL_BLOCKER` | Requiere dominio y cambios DNS del propietario |
| SMTP real | `EXTERNAL_BLOCKER` | Requiere proveedor y credenciales |
| Sentry/alertas externas | `EXTERNAL_BLOCKER` | Requiere proyecto y credenciales |
| Backups, PITR y restore real | `EXTERNAL_BLOCKER` | Requiere configuracion y ejecucion sobre Railway |
| Production cutover | `EXTERNAL_BLOCKER` | Requiere autorizacion final y credenciales operativas |

## Roadmap por dependencias

| Fase | Epic | Resultado exigido | Estado |
| --- | --- | --- | --- |
| A | Local AI Orchestrator | Delegacion aislada, gates, metricas y flujo de revision | `TESTED` |
| B | Production Foundation V1.2.3 | Version coherente, preflight, smoke tests, runbooks y gate de release | En curso |
| C | Intervention Traceability | Timeline inmutable, varios tecnicos, sesiones, notas, estados y validacion | Pendiente |
| D | Users and Notifications | Invitaciones, ciclo de usuario, notificaciones internas y correo | Pendiente |
| E | Preventive Maintenance | Checklists reutilizables, recurrencias y ejecucion trazable | Pendiente |
| F | Inventory Integration | Consumo transaccional por OT, stock, coste e historial | Pendiente |
| G | Technician PWA | Flujo movil rapido, cola offline util y conflictos visibles | Pendiente |
| H | Reporting | Parte PDF, KPIs operativos y dashboard accionable | Pendiente |
| I | Product UX | Responsive 375/tablet/desktop, accesibilidad, estados y consistencia | Pendiente |
| J | Commercial Readiness | Demo, tutorial, onboarding, ayuda, documentos cliente y sitio comercial | Pendiente |
| K | Assurance | Auditoria de seguridad, rendimiento, carga y recuperacion | Pendiente |
| L | Release Candidate | E2E critico, soak staging, cierre de riesgos y GO/NO-GO | Pendiente |
| M | Production Release | Cutover autorizado, observacion y validacion productiva | Bloqueado hasta aprobacion |

## Backlog activo

### Phase B - Production Foundation V1.2.3

- `AI-0101`: alinear metadatos de version V1.2.3 en runtime y artefactos.
- `FO-0102`: implementar un smoke test de release reutilizable para staging y produccion.
- `FO-0103`: endurecer workflows con preflight de version, tag y endpoints.
- `FO-0104`: documentar matriz de variables, rollback y registro de despliegue.
- `FO-0105`: ejecutar gates locales y CI; validar staging si se habilita.

### Phase C - Intervention Traceability

- `FO-0201`: migracion aditiva para participantes, sesiones y timeline.
- `AI-0202`: modelos, schemas y consultas tenant-scoped.
- `AI-0203`: endpoints de participante y ciclo start/pause/resume/finish.
- `FO-0204`: reglas de transicion, concurrencia, permisos y auditoria inmutable.
- `AI-0205`: pruebas de API, aislamiento, permisos y tiempos por tecnico.
- `AI-0206`: detalle de OT orientado a movil con acciones de una pulsacion.
- `AI-0207`: timeline legible y gestion de participantes para responsables.

### Phase D en adelante

Las tareas se concretan al cerrar la fase anterior. Ninguna feature se marca terminada sin backend, frontend, permisos, aislamiento, errores, responsive, pruebas y revision.

## Gates de promocion

Una entrega solo puede promocionarse cuando:

1. `ruff`, `pytest`, Alembic, lint, typecheck, tests frontend y builds pasan.
2. No hay cambios fuera del scope ni secretos en Git.
3. Las migraciones son compatibles hacia atras y tienen downgrade revisable.
4. Los accesos multiempresa y roles tienen pruebas negativas.
5. Staging pasa smoke y validacion profunda antes de etiquetar una release.
6. Produccion exige aprobacion manual, tag validado y rollback preparado.

## Bloqueos externos agrupados

Para convertir `IMPLEMENTED/TESTED` en `STAGING_VALIDATED/PRODUCTION_VALIDATED` se necesitara, en una unica ventana operativa:

1. Habilitar `RAILWAY_STAGING_ENABLED` y confirmar el secret de Railway del environment `staging`.
2. Confirmar plan de PostgreSQL, backups/PITR y bucket con retencion.
3. Facilitar dominios/DNS, SMTP y observabilidad cuando se contraten.
4. Autorizar expresamente el cutover de produccion.

