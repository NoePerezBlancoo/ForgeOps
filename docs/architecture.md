# Arquitectura de ForgeOps

ForgeOps V1.0 es un monolito modular con dos aplicaciones desplegables, almacenamiento documental privado y PostgreSQL con `pgvector`.

```text
Browser -> Next.js -> FastAPI -> PostgreSQL + pgvector
                       |   |
                       |   +-> volumen privado de documentos
                       |
                       +-> OpenAI opcional
```

## Modulos

```text
auth        identidad, tokens y sesiones
companies   configuracion empresarial
plants      centros productivos
users       equipo y permisos
audit       trazabilidad administrativa
assets      maestro de equipos
incidents   averias y seguimiento
work_orders ejecucion del mantenimiento
maintenance planificacion preventiva
inventory   repuestos y movimientos
documents   archivos privados
ai          ingesta, recuperacion y RAG
dashboard   KPIs y onboarding
```

## Decisiones

- UUID para identificadores publicos.
- `company_id` obligatorio en toda entidad empresarial.
- Consultas acotadas desde el usuario autenticado, nunca desde datos enviados por el navegador.
- Selector de planta como filtro opcional dentro de la empresa autorizada.
- Access token corto y refresh token rotatorio almacenado como hash.
- Permisos centralizados por rol y reglas adicionales en el dominio.
- Alembic como unica via de evolucion del esquema.
- Semilla idempotente apoyada en restricciones unicas.
- Archivos fuera del directorio publico y descargas autenticadas.
- Auditoria separada de los datos operativos y conservacion del actor cuando existe.

## Limites de dominio

Los servicios validan relaciones cruzadas antes de escribir: una orden no puede apuntar a un activo de otra planta, un responsable debe pertenecer a la empresa y un documento solo se recupera dentro de su tenant. Desactivar usuarios revoca sesiones; eliminar el ultimo administrador o desactivar una planta con activos se rechaza.

## Inteligencia documental

La ingesta extrae TXT, PDF y DOCX, normaliza el texto y crea fragmentos solapados. Cada fragmento conserva empresa, documento, activo y pagina. La reindexacion reemplaza los fragmentos anteriores y la restriccion `(document_id, chunk_index)` evita duplicados.

El modo local utiliza recuperacion lexica y respuestas extractivas. El modo OpenAI calcula embeddings, consulta `pgvector` por distancia coseno y genera con evidencia limitada. Los umbrales absolutos y relativos evitan presentar los fragmentos menos malos como si fueran relevantes.

## Despliegue

Los tres servicios se ejecutan con Docker Compose y healthchecks. El backend migra y prepara datos al iniciar. Para un piloto, PostgreSQL y los volumentes deben respaldarse, los servicios deben quedar detras de TLS y solo el proxy debe estar expuesto. Consulta [pilot-deployment.md](pilot-deployment.md).
