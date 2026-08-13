# ADR-012: Checklists preventivos y generacion programada

## Estado

Aceptada e implementada el 2026-08-13.

## Contexto

Un plan preventivo necesita un procedimiento reutilizable, pero una orden ya emitida debe conservar exactamente el trabajo que se esperaba en ese momento. Editar una plantilla no puede alterar evidencias historicas ni permitir cerrar una intervencion con verificaciones obligatorias pendientes.

## Decision

- Separar plantillas y pasos reutilizables de los pasos ejecutables de cada orden.
- Mantener una referencia opcional desde el plan a su plantilla activa.
- Copiar titulo, instrucciones, orden y obligatoriedad a `work_order_checklist_items` al generar la OT.
- Bloquear el plan durante la generacion para evitar ordenes concurrentes duplicadas y avanzar su siguiente fecha en la misma transaccion.
- Registrar usuario y fecha de cada comprobacion, junto con un evento inmutable `CHECKLIST_UPDATED`.
- Aplicar version optimista por paso y responder `409 Conflict` ante una escritura obsoleta.
- Impedir completar una OT mientras exista un paso obligatorio pendiente.
- Ejecutar la generacion periodica mediante un comando sin estado que recorre empresas activas bajo contexto `system` y restablece el contexto tenant antes de operar.
- Incluir `company_id`, indices y RLS forzado en todas las tablas nuevas.

## Consecuencias

Las plantillas pueden evolucionar sin reescribir ordenes antiguas. La copia aumenta moderadamente el almacenamiento, pero preserva trazabilidad, simplifica el uso offline futuro y evita depender de una version mutable. El scheduler puede ejecutarse como Railway Cron sin incorporar un segundo sistema de planificacion dentro de la API.

## Verificacion

- Migracion `upgrade/downgrade/upgrade` y `alembic check` sin diferencias.
- Generacion, snapshot historico, concurrencia, cierre obligatorio y permisos cubiertos por pruebas.
- Aislamiento de las tres tablas nuevas verificado con el rol PostgreSQL runtime.
- Seed ejecutado dos veces sin duplicados.
- Recorrido visual de plan, plantilla y OT validado en escritorio y movil.
