# Almacenamiento documental

`StorageService` desacopla dominio y proveedor. Local usa un volumen para desarrollo/demo; staging y produccion exigen S3 compatible.

## Claves

```text
companies/{company_uuid}/assets/{asset_uuid}/documents/{file_uuid}.{ext}
```

El nombre original se conserva como metadato, nunca como ruta. La lectura vuelve a validar el prefijo del tenant para impedir traversal o acceso cruzado.

## Railway Bucket

Configurar `STORAGE_BACKEND=s3`, endpoint, access key, secret, bucket y region mediante referencias. Para buckets Railway actuales usar `S3_FORCE_PATH_STYLE=false`; confirmar el estilo en Credentials porque buckets antiguos pueden requerir path style.

El bucket no es publico. El backend crea URL firmada con `STORAGE_SIGNED_URL_SECONDS` y no expone credenciales al navegador.

## Limites y consumo

El upload se corta por `MAX_UPLOAD_BYTES`; planes aplican limite total de storage antes de persistir metadatos. El backoffice muestra bytes agregados, no contenido. La eliminacion debe coordinar objeto, registro, chunks RAG y auditoria; no se realizan limpiezas automaticas peligrosas.

## Fallos

Si S3 falla, la API devuelve 503 con request ID. No se hace fallback local en produccion. Jobs idempotentes permiten repetir indexacion/correo sin duplicar el efecto logico.

## Retencion

Configurar versionado o backup del bucket separado del backup PostgreSQL. Una restauracion consistente debe validar que cada `storage_key` de DB existe y que ningun prefijo de otra empresa se devuelve al usuario actual.
