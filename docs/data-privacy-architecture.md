# Arquitectura de privacidad

Este documento describe controles tecnicos para clientes europeos; no sustituye asesoramiento ni textos legales.

## Clasificacion

- Datos de cuenta: nombre, correo, rol, sesiones y actividad.
- Datos industriales: plantas, activos, incidencias, ordenes y documentos.
- Datos operativos ForgeOps: empresa, plan, limites, auditoria y jobs.
- Telemetria: request IDs, estado, latencia y errores sin contenido sensible innecesario.

## Retencion propuesta

| Categoria | Politica inicial |
| --- | --- |
| Auditoria | 24 meses o contrato; ampliar para trazabilidad regulada |
| Sesiones revocadas/reset | purga segura tras 90 dias |
| Logs de aplicacion | 30-90 dias con acceso restringido |
| Documentos | vida del contrato y periodo de salida acordado |
| Trials abandonados | aviso, gracia y borrado tras politica comercial |
| Historico industrial | conservar/anominizar tras evaluar dependencias |

No se implementan borrados automaticos en V1.2.1. La politica debe aprobarse antes de programarlos.

## Exportacion

La arquitectura permite exportar por `company_id`: metadatos JSON/CSV, documentos bajo el prefijo S3 del tenant, auditoria y manifiesto con checksums. La exportacion sera un job idempotente, cifrado, de corta disponibilidad y auditado. No esta completa en esta version.

## Destruccion de tenant

No existe `DELETE /companies/{id}`. El workflow futuro requiere solicitud verificada, doble confirmacion, periodo de gracia, bloqueo de escritura, backup/export opcional, borrado ordenado de DB y bucket, verificacion de referencias y evento de auditoria inmutable.

## Usuarios historicos

La desactivacion conserva autorias. Cuando proceda un derecho de supresion, se anonimizaran identificadores personales sin eliminar ordenes, intervenciones o requisitos legales de mantenimiento. Cualquier excepcion debe quedar documentada.

## Acceso

El operador ve metadatos comerciales y agregados. Soporte sobre datos industriales necesitara consentimiento, motivo y caducidad. Backups, exportaciones y restauraciones usan entornos restringidos y se destruyen al finalizar la operacion.
