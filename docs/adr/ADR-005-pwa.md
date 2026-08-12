# ADR-005: Cliente PWA

## Contexto
Tecnicos usan movil/tablet, pueden tener mala cobertura y no necesitan una app nativa completa.

## Decision
Convertir Next.js en PWA instalable y limitar offline a borradores operativos explicitos en IndexedDB.

## Alternativas
App nativa duplica desarrollo. Cachear toda la API aumenta riesgo de privacidad y conflictos.

## Consecuencias
El service worker nunca cachea API/control. Cada flujo offline futuro necesita contrato de conflicto e idempotencia antes de habilitarse.
