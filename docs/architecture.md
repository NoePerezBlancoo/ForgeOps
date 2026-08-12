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

## Estado de V0.2

Esta version implementa autenticacion, empresas, plantas, usuarios, activos, incidencias, ordenes, preventivos, inventario, documentos y dashboard. Los archivos tecnicos se guardan fuera del directorio publico y se sirven despues de validar usuario y empresa. Los directorios de IA e integraciones mantienen contratos de extension para las siguientes iteraciones.
