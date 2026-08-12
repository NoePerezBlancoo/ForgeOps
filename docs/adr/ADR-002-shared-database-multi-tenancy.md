# ADR-002: Multi-tenancy en base compartida

## Contexto
El producto necesita aprovisionamiento inmediato y operacion economica para pymes sin perder aislamiento.

## Decision
Compartir esquema y base, identificando toda entidad de negocio por `company_id`. Aplicar aislamiento en servicios y PostgreSQL RLS.

## Alternativas
Schema o base por tenant ofrecen aislamiento fisico mayor, pero multiplican migraciones, pools y recuperaciones en esta etapa.

## Consecuencias
Cada tabla/query nueva exige revision tenant, indice por empresa y prueba cruzada. Enterprise podra evolucionar a despliegue dedicado sin cambiar el dominio.
