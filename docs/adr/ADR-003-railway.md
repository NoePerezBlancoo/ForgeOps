# ADR-003: Railway como plataforma inicial

## Contexto
ForgeOps requiere frontend, API, worker, PostgreSQL, Redis, bucket, dominios y entornos con baja carga operativa.

## Decision
Preparar Railway como plataforma inicial mediante Dockerfiles, Config as Code, variables y servicios desacoplados.

## Alternativas
Kubernetes ofrece mas control con coste excesivo. Un VPS reduce servicios gestionados y aumenta guardias. Vercel no ejecuta el backend Python/worker persistente completo.

## Consecuencias
El despliegue real depende de cuenta y recursos Railway. El codigo sigue portable porque usa PostgreSQL, Redis y S3 estandar.
