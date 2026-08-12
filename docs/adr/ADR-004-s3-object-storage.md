# ADR-004: Storage S3 compatible

## Contexto
Contenedores y replicas no pueden depender de disco local para documentos tecnicos.

## Decision
Usar una interfaz de storage con implementaciones local y S3. Produccion exige bucket privado, claves UUID y URLs firmadas.

## Alternativas
Volumen compartido limita replicas y portabilidad. Guardar binarios en PostgreSQL aumenta backup y carga de DB.

## Consecuencias
DB y bucket deben recuperarse de forma consistente. Cambiar Railway Bucket por otro S3 no altera el dominio.
