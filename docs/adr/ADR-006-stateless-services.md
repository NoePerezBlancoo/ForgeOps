# ADR-006: Servicios stateless

## Contexto
Railway puede reemplazar o replicar contenedores durante deploys y failovers.

## Decision
Backend y frontend no conservan sesion ni archivos en memoria/disco persistente. PostgreSQL guarda sesiones, Redis coordina limites/cola y S3 guarda documentos.

## Alternativas
Sticky sessions y volumen de aplicacion dificultan escalado y recuperacion.

## Consecuencias
Se pueden ejecutar varias replicas sin afinidad. Dependencias externas son esenciales para readiness y deben monitorizarse.
