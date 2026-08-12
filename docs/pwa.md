# PWA y conectividad

ForgeOps incluye manifest, iconos 192/512, service worker, estado online/offline e instalacion cuando el navegador expone el evento correspondiente.

## Cache

El service worker aplica network-first a navegacion y cachea solo recursos estaticos controlados. No cachea `/api/` ni `/control`, evitando conservar respuestas industriales o del operador. Si una navegacion falla, muestra `/offline`.

## Cola local

IndexedDB admite exclusivamente borradores de incidencia, notas de orden e inspecciones. Estados: `PENDING`, `SYNCING`, `FAILED`, `CONFLICT`. No se guardan contrasenas, JWT, datos de operador, documentos ni acciones administrativas.

La sincronizacion debe conservar idempotency key y version de entidad. Un `409` se presenta como conflicto; no sobrescribe silenciosamente trabajo remoto. En esta base la cola y estados estan preparados, mientras el envio automatico de cada formulario se integrara por modulo cuando sus contratos offline sean definitivos.

## UX

La aplicacion muestra conectividad y pendientes sin bloquear lectura ya cargada. Los controles tactiles mantienen dimensiones estables. Recuperacion, mantenimiento y errores globales tienen pantallas propias sin detalles tecnicos.

## Validacion

1. Abrir la aplicacion por HTTPS o localhost.
2. Confirmar manifest e iconos en DevTools > Application.
3. Confirmar que `sw.js` controla una recarga.
4. Activar Offline, navegar y comprobar `/offline`.
5. Verificar que API y `/control` no aparecen en Cache Storage.
6. Probar instalacion en Chromium Android y escritorio.
