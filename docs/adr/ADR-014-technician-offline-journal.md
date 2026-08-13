# ADR-014: Diario offline del tecnico

## Estado

Aceptada e implementada en Phase G.

## Contexto

Los tecnicos pueden perder cobertura durante una averia. Cachear respuestas API o permitir todas las mutaciones sin red expondria datos entre cuentas y produciria conflictos silenciosos en stock, tiempos y estados.

## Decision

ForgeOps mantiene una identidad local sin credenciales durante 24 horas, snapshots de solo lectura y una cola IndexedDB aislada por empresa y usuario. Solo se habilitan operaciones con contrato idempotente en servidor: alta de incidencia y nota de orden.

El motor de sincronizacion no accede a React, fetch, tokens ni almacenamiento. Recibe dependencias, procesa por fecha y clasifica respuestas HTTP. Los conflictos quedan visibles y requieren una decision explicita.

El service worker cachea pantallas visitadas y recursos estaticos, pero excluye API y backoffice. Cerrar sesion elimina identidad, snapshots y operaciones locales del usuario.

## Consecuencias

- Un reintento no duplica eventos de negocio.
- Las acciones concurrentes permanecen online-only.
- La lectura offline depende de haber visitado antes la pantalla.
- Fotografias y checklist requeriran contratos propios antes de entrar en la cola.
- El dispositivo sigue siendo una frontera de confianza operativa y debe bloquearse fisicamente.
