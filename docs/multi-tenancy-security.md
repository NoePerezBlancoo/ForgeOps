# Seguridad multiempresa

ForgeOps usa una base PostgreSQL compartida con `company_id` en toda entidad industrial. La separacion se aplica en dos capas obligatorias.

## Capa de aplicacion

- El JWT identifica usuario y empresa; el servidor no acepta `company_id` arbitrario del cliente.
- Servicios y validaciones filtran empresa, planta, activo y usuario relacionado.
- IDs publicos son UUID y no sustituyen la autorizacion.
- Busquedas, documentos y RAG incluyen empresa antes de ordenar o puntuar resultados.
- Operadores de plataforma tienen una identidad global separada y no reutilizan cuentas de clientes.

## Capa PostgreSQL

Las tablas de tenant tienen RLS `ENABLE` y `FORCE`. La conexion runtime usa un rol sin `SUPERUSER`, sin `BYPASSRLS` y no propietario. Cada transaccion establece variables locales:

- `tenant`: solo filas de `app.company_id`.
- `auth`: lectura minima para autenticar y recuperar acceso.
- `signup`: alta atomica de empresa y administrador.
- `platform`: agregados y gobierno comercial del operador.
- `system`: jobs internos controlados.

El contexto se aplica con `set_config(..., true)`, por lo que desaparece al terminar la transaccion. No se debe ejecutar una query antes de establecerlo.

## Pruebas de ataque

`tests/test_postgres_rls.py` utiliza PostgreSQL real y un rol restringido. Comprueba lectura del tenant A, ocultacion explicita de B, rechazo de escritura cruzada y acceso agregado de plataforma. La suite funcional tambien valida referencias cruzadas de plantas, activos, usuarios, incidencias, ordenes y documentos.

## Operacion

- Revisar nuevas tablas en cada migracion para incluir RLS e indices tenant.
- Nunca declarar `DATABASE_USER_IS_RESTRICTED=true` sin verificar `rolsuper=false` y `rolbypassrls=false`.
- Las tareas worker deben establecer contexto `system` o tenant antes de consultar.
- Una exportacion o soporte futuro debe usar un workflow auditado; no se implementa impersonacion silenciosa.
