# Inteligencia documental

## Flujo de indexacion

1. Un usuario autorizado carga un TXT, PDF o DOCX vinculado a un activo.
2. El archivo se guarda en un volumen privado con un nombre interno no predecible.
3. El backend extrae y normaliza el texto con un limite configurable.
4. El contenido se divide en fragmentos solapados que conservan documento, activo y pagina.
5. En modo OpenAI se calculan embeddings de 1536 dimensiones.
6. PostgreSQL almacena los fragmentos y actualiza el estado de indexacion.

Los formatos sin extraccion de texto se conservan y descargan normalmente, pero quedan marcados como `UNSUPPORTED` para el asistente.

## Flujo de consulta

1. La API valida la identidad, empresa y activo opcional.
2. Recupera solo fragmentos `READY` de esa empresa.
3. En modo local aplica ranking lexico; en modo OpenAI usa similitud coseno.
4. La respuesta se construye exclusivamente con la evidencia recuperada.
5. Cada fuente expone documento, activo, pagina, extracto y enlace autenticado.
6. La consulta se registra para trazabilidad y diagnostico.

## Limites de confianza

- El asistente apoya la consulta documental; no sustituye procedimientos aprobados ni decisiones de seguridad.
- Una respuesta sin evidencia suficiente se rechaza de forma explicita.
- Las citas permiten contrastar siempre el texto original.
- El contenido de los documentos se trata como datos, no como instrucciones para el modelo.
- La aplicacion no almacena claves de proveedor en base de datos ni las entrega al navegador.
- La busqueda vectorial solo esta disponible cuando el servidor tiene OpenAI configurado y los documentos se han reindexado con embeddings.

## Operacion

El panel `Asistente documental` muestra documentos listos, pendientes, fallidos y no compatibles. Los responsables de mantenimiento y administradores pueden indexar o reindexar; los perfiles de consulta solo pueden buscar y descargar fuentes autorizadas.
