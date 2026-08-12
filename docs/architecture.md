# Arquitectura de ForgeOps

ForgeOps es un monolito modular con dos aplicaciones desplegables y una base de datos PostgreSQL.

```text
Browser -> Next.js -> FastAPI -> PostgreSQL
                       |
                       +-> ai/ (contratos futuros)
                       +-> integrations/ (adaptadores futuros)
```

## Decisiones principales

- Los identificadores publicos son UUID.
- Toda entidad operativa incluye `company_id` y se consulta desde el contexto autenticado.
- El access token JWT es corto; el refresh token rota y se almacena como hash en base de datos.
- Los permisos se resuelven por rol en una unica capa de dependencias.
- Los modulos de dominio exponen modelos, esquemas, servicios y rutas pequenas.
- Alembic es la unica via de evolucion del esquema.
- La carga demo es idempotente y se apoya en claves unicas para impedir duplicados.

## Limites de V0.1

Esta version implementa autenticacion, empresas, plantas, usuarios, activos, incidencias, ordenes y dashboard. Los directorios de preventivos, inventario, documentos, IA e integraciones contienen contratos de extension, pero su funcionalidad pertenece a iteraciones posteriores.

