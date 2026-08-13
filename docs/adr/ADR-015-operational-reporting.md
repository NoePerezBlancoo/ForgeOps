# ADR-015: Reporting operativo

## Estado

Aceptada e implementada en Phase H.

## Contexto

El dashboard inicial mostraba volumen por estado, pero no permitia priorizar trabajo vencido, identificar activos con mayor impacto ni entender la carga del equipo.

## Decision

El dashboard utiliza PostgreSQL como fuente de verdad y aplica siempre `company_id`, planta opcional y un periodo permitido de 7, 30, 90 o 365 dias. El endpoint de exportacion reutiliza el mismo servicio que la pantalla.

Definiciones:

- `Horas de parada`: suma de `downtime_minutes` de incidencias informadas dentro del periodo.
- `MTTR`: media de horas entre `reported_at` y `resolved_at` para incidencias resueltas dentro del periodo.
- `OT vencida`: orden abierta, asignada, en curso o en espera con fecha planificada anterior al momento de consulta.
- `Preventivo vencido`: plan activo cuya proxima ejecucion es anterior al momento de consulta.
- `Activo de mayor impacto`: activo ordenado por horas de parada y, en empate, por numero de incidencias del periodo.
- `Carga de tecnico`: ordenes activas donde participa actualmente; se separan ordenes en curso y sesiones abiertas.

Cada periodo incluye el dia actual y los `N - 1` dias naturales anteriores. Las tendencias usan dias para periodos de hasta 30 dias y semanas para periodos superiores. Los resultados extensos permanecen en sus listados paginados; el dashboard limita rankings.

## Consecuencias

- Pantalla y CSV mantienen el mismo alcance multiempresa.
- Las metricas son reproducibles y defendibles comercialmente.
- El MTTR aparece como `Sin datos` cuando no existen resoluciones suficientes.
- Los indicadores actuales son operativos; analitica financiera y OEE quedan fuera hasta disponer de datos fiables.
