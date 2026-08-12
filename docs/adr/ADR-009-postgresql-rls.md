# ADR-009: PostgreSQL Row Level Security

## Contexto
Un filtro de aplicacion omitido podria exponer filas de otra empresa.

## Decision
Activar y forzar RLS en tablas tenant. Establecer contexto transaccional y ejecutar con rol restringido sin bypass.

## Alternativas
Confiar solo en ORM reduce defensa en profundidad. Vistas por tenant complican escrituras y evolucion del esquema.

## Consecuencias
Migrations y jobs deben definir contexto. Autenticacion/signup/plataforma usan politicas especificas. CI ejecuta un ataque cruzado sobre PostgreSQL real.
