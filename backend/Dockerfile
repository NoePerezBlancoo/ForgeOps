FROM python:3.12-slim

LABEL org.opencontainers.image.title="ForgeOps Backend" \
      org.opencontainers.image.description="ForgeOps industrial CMMS API and worker runtime" \
      org.opencontainers.image.version="1.2.2" \
      org.opencontainers.image.source="https://github.com/NoePerezBlancoo/ForgeOps"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

ARG INSTALL_DEV=false
COPY requirements.txt requirements-dev.txt ./
RUN if [ "$INSTALL_DEV" = "true" ]; then \
      pip install --no-cache-dir -r requirements-dev.txt; \
    else \
      pip install --no-cache-dir -r requirements.txt; \
    fi

COPY . .
RUN chmod +x /app/entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["/app/entrypoint.sh"]
