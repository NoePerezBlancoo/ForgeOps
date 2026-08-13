# ADR-013: Inventario transaccional integrado con ordenes

## Estado

Aceptada e implementada el 2026-08-13.

## Contexto

Una empresa necesita conocer que material se utilizo en cada averia, quien lo retiro, cuanto coste tuvo y que parte regreso al almacen. Editar o eliminar un consumo historico destruiria la trazabilidad tecnica y economica. Dos operarios tambien pueden actuar sobre la misma referencia al mismo tiempo, por lo que una comprobacion de stock sin concurrencia no es suficiente.

## Decision

- Tratar `inventory_movements` como un libro inmutable de entradas, consumos, ajustes y devoluciones.
- Vincular opcionalmente cada movimiento con una orden de trabajo y cada devolucion con su consumo original.
- Representar consumos con cantidad negativa y coste total positivo; las devoluciones usan cantidad positiva y coste total negativo.
- Congelar el coste unitario vigente al crear el consumo y reutilizarlo en sus devoluciones.
- Calcular el coste material de la OT como suma de costes firmados, sin depender del precio actual del maestro.
- Bloquear la fila de inventario y exigir su version esperada antes de cambiar el saldo.
- Rechazar stock negativo, devoluciones superiores al consumo remanente y movimientos sobre ordenes cerradas o canceladas.
- Permitir actuar a responsables y participantes activos; aplicar el entitlement de Inventario en la propia API.
- Registrar eventos de OT, auditoria administrativa y notificaciones al cruzar el nivel minimo.
- Mantener `company_id` y RLS forzado en referencias y movimientos.
- Validar en PostgreSQL que repuesto, orden y consumo revertido pertenecen al mismo tenant que el movimiento.

## Consecuencias

El historial permite reconstruir saldos, autoria y coste de una intervencion aunque cambie el precio del repuesto. Una correccion se expresa con un movimiento compensatorio, por lo que aumenta el numero de filas pero no se pierde evidencia. El control de version devuelve `409 Conflict` y obliga al cliente a refrescar cuando otro usuario modifica el stock.

## Verificacion

- Migracion `upgrade/downgrade/upgrade`, `check_migrations` y `alembic check` sin diferencias.
- Consumo, devolucion parcial, exceso de devolucion, coste neto, saldo insuficiente y version obsoleta cubiertos por API.
- Lecturas y escrituras cruzadas bloqueadas con el rol PostgreSQL runtime.
- 66 pruebas backend, 5 pruebas RLS y 84,28 % de cobertura ejecutadas.
- Flujo real validado en inventario y OT a 390 y 1280 px sin desbordamiento horizontal.
