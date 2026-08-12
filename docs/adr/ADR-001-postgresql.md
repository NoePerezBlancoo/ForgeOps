# ADR-001: PostgreSQL como sistema de registro

## Contexto
ForgeOps necesita transacciones, relaciones industriales, auditoria, busqueda y vectores documentales.

## Decision
Usar PostgreSQL con Alembic y pgvector como fuente de verdad. Redis es efimero/cola y S3 conserva binarios.

## Alternativas
MySQL habria mantenido experiencia previa pero no aporta la misma integracion RLS/pgvector. Una base por cliente aumenta coste operativo prematuramente.

## Consecuencias
Se requiere operacion PostgreSQL, backups/PITR, migraciones compatibles e indices revisados. La aplicacion no depende de extensiones fuera de pgvector.
