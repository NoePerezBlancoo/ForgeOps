# ADR-010: Trazabilidad de intervenciones por eventos y sesiones

## Estado

Aceptada para implementar en Phase C.

## Contexto

La orden actual conserva un unico tecnico asignado, fechas agregadas y observaciones mutables. Ese modelo permite coordinar trabajo sencillo, pero no reconstruir una averia industrial con varios participantes, pausas, tiempos individuales, cambios de estado y validacion responsable.

La trazabilidad debe seguir siendo comprensible, tenant-scoped y robusta ante ediciones concurrentes. Los hechos historicos no pueden depender de comparar solamente el estado actual de la orden.

## Decision

Mantener `work_orders` como agregado operativo e introducir tres conceptos aditivos:

1. `work_order_participants`: tecnicos que participan, con rol, alta y retirada logica.
2. `work_sessions`: intervalos de trabajo por participante con inicio, pausa/final y duracion derivable.
3. `work_order_events`: timeline append-only con actor, tipo, fecha, resumen y payload estructurado minimo.

El campo `assigned_to` se mantiene durante la transicion como tecnico principal para compatibilidad. Toda nueva asignacion sincroniza el participante principal dentro de la misma transaccion.

Los comandos de dominio seran explicitos: asignar, iniciar, pausar, reanudar, anotar, finalizar, validar y cerrar. No se inferiran hechos historicos a partir de un `PATCH` generico. El servicio bloqueara la orden o la sesion afectada durante transiciones sensibles y rechazara comandos incompatibles con `409 Conflict`.

Los eventos se insertan en la misma transaccion que el cambio operativo. La API no ofrece update ni delete de eventos. Las correcciones se expresan mediante un nuevo evento enlazado al anterior y quedan auditadas.

## Reglas principales

- Todas las filas incluyen `company_id` y quedan cubiertas por RLS.
- Un usuario desactivado conserva autoria y participacion historica.
- Un tecnico solo opera ordenes en las que participa o que tiene asignadas.
- Solo puede existir una sesion abierta por tecnico y orden.
- Pausar o finalizar cierra la sesion abierta con fecha de servidor.
- El tiempo total se calcula desde sesiones; los campos agregados son cache opcional, nunca fuente unica.
- Completar exige trabajo realizado y una causa/solucion cuando la orden es correctiva.
- Validar o cerrar requiere responsable autorizado y orden completada.
- Las fechas se almacenan en UTC y se muestran en la zona horaria de la empresa.
- Fotografias, documentos y consumos futuros referencian la orden y generan eventos.

## Consecuencias

La migracion es aditiva y compatible con la version anterior. El modelo incrementa el numero de tablas y comandos, pero permite tiempos por tecnico, timeline fiable, parte PDF y consumo de materiales sin convertir `work_orders` en una tabla monolitica.

La primera entrega no incluye firma criptografica, geolocalizacion ni borrado de hechos. Una firma visual opcional se tratara como evidencia privada y evento posterior, con politica de privacidad especifica.
