# Arquitectura de ForgeOps

ForgeOps es un monolito modular con dos aplicaciones desplegables, almacenamiento documental privado y PostgreSQL con `pgvector`.

```text
Browser -> Next.js -> FastAPI -> PostgreSQL + pgvector
                       |   |
                       |   +-> volumen privado de documentos
                       |
                       +-> OpenAI opcional
```

## Decisiones principales

- Los identificadores publicos son UUID.
- Toda entidad operativa incluye `company_id` y se consulta desde el contexto autenticado.
- El access token JWT es corto; el refresh token rota y se almacena como hash.
- Los permisos se resuelven por rol en una unica capa de dependencias.
- Los modulos de dominio exponen modelos, esquemas, servicios y rutas pequenas.
- Alembic es la unica via de evolucion del esquema.
- La carga demo es idempotente y se apoya en claves unicas para impedir duplicados.
- Los documentos nunca se publican directamente; cada descarga valida usuario y empresa.
- Los fragmentos y consultas de IA conservan `company_id` para evitar recuperacion cruzada.

## Inteligencia documental V0.3

La ingesta extrae texto de TXT, PDF y DOCX, lo normaliza y divide en fragmentos con solapamiento. Cada fragmento queda vinculado a empresa, documento y activo. La reindexacion sustituye los fragmentos anteriores dentro de una transaccion logica, evitando duplicados.

El modo local realiza recuperacion lexica y genera respuestas extractivas citadas. El modo OpenAI calcula embeddings, usa distancia coseno sobre `pgvector` y genera la respuesta con instrucciones estrictas para limitarla a la evidencia recuperada. Si el proveedor externo falla, la consulta conserva un resultado extractivo local.

Las preguntas y respuestas quedan registradas con usuario, empresa, activo, modo, proveedor, confianza, fuentes y duracion. La clave del proveedor solo se lee desde el entorno del backend.

Consulta [document-intelligence.md](document-intelligence.md) para el flujo operativo y sus limites de confianza.
