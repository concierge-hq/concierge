FROM python:3.12-slim

LABEL org.opencontainers.image.source="https://github.com/concierge-hq/concierge"
LABEL org.opencontainers.image.description="Concierge MCP runtime — base image with concierge-sdk preinstalled"
LABEL org.opencontainers.image.licenses="MIT"

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

ARG CONCIERGE_VERSION=0.8.0
ARG CONCIERGE_EXTRAS=""
RUN pip install "concierge-sdk${CONCIERGE_EXTRAS}==${CONCIERGE_VERSION}"

WORKDIR /app
EXPOSE 8000
