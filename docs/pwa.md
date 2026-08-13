# PWA y conectividad

ForgeOps es instalable en escritorio, tablet y movil. El modo offline esta orientado a contingencias de cobertura en planta y conserva limites explicitos para proteger la consistencia industrial.

## Sesion y aislamiento local

Tras un acceso online correcto se guarda una identidad local sin tokens durante un maximo de 24 horas. La cola y los snapshots se separan por `company_id` y `user_id`; cerrar sesion elimina los datos locales de esa cuenta. En dispositivos compartidos el usuario debe cerrar sesion al terminar.

El modo offline nunca permite entrar al backoffice `/control` ni renueva permisos. Una cuenta caducada debe volver a autenticarse online.

## Cache y snapshots

El service worker aplica network-first y guarda el shell de las pantallas visitadas para poder abrirlas sin red. Nunca cachea `/api/` ni `/control`. IndexedDB conserva las ultimas plantas, activos, opciones, incidencias y ordenes consultadas por el usuario.

Los snapshots son de solo lectura. Inventario, transiciones, tiempos, checklist, validaciones y administracion requieren conexion porque dependen de concurrencia o autorizacion actual.

## Cola local

La version actual admite dos operaciones:

- alta de incidencia;
- nota de orden de trabajo.

Cada operacion incorpora un UUID generado por el cliente. PostgreSQL impone unicidad por tenant, autor y entidad para que una respuesta perdida o un reintento no duplique incidencias, notas, eventos ni notificaciones.

Estados: `PENDING`, `SYNCING`, `FAILED` y `CONFLICT`. La sincronizacion se ejecuta al recuperar red o por accion del usuario, procesa cronologicamente y detiene el lote ante una nueva perdida de conectividad. Un `409` queda visible para revision manual; no se aplica last-write-wins.

No se guardan contrasenas, JWT, datos de operador, documentos, fotografias ni acciones administrativas.

## Validacion

1. Abrir ForgeOps por HTTPS o localhost e iniciar sesion.
2. Visitar incidencias y ordenes para generar snapshots.
3. Confirmar manifest, iconos y control de `sw.js` en DevTools.
4. Activar Offline y recargar una pantalla visitada.
5. Crear una incidencia y una nota; comprobarlas en `/sync`.
6. Recuperar red y verificar un unico registro remoto por operacion.
7. Confirmar que Cache Storage no contiene API ni `/control`.
8. Cerrar sesion y comprobar que IndexedDB no conserva datos de la cuenta.
