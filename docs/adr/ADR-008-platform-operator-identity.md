# ADR-008: Identidad global de operador

## Contexto
El propietario debe gestionar trials y suscripciones sin pertenecer a una empresa ni reutilizar sus permisos.

## Decision
Crear operadores, sesiones, tokens, cookies y auditoria independientes con TOTP obligatorio y backoffice `/control`.

## Alternativas
Un superadmin tenant mezcla planos de seguridad. Impersonacion automatica expone datos industriales innecesarios.

## Consecuencias
El operador gobierna metadatos comerciales y agregados. Soporte futuro requerira consentimiento, motivo, caducidad y auditoria.
