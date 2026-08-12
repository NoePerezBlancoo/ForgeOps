# ADR-007: Redis y worker RQ

## Contexto
Correo, extraccion, embeddings e integraciones no deben aumentar latencia HTTP ni perderse en reinicios.

## Decision
Persistir el job cifrado e idempotente en PostgreSQL y distribuirlo con Redis/RQ usando serializador JSON y reintentos acotados.

## Alternativas
Tareas en background de FastAPI se pierden al reiniciar. Celery aporta complejidad innecesaria para el volumen inicial.

## Consecuencias
El worker puede escalar separado. La tabla permite recuperar trabajos pendientes tras una caida de Redis y auditar fallos sin guardar payload en claro.
