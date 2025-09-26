# syntax=docker/dockerfile:1

##########################################
# 1. Gets uv for the building platform
FROM ghcr.io/astral-sh/uv:latest AS uv

##########################################
# 2. Base operating system with non-root user
FROM python:3.12-slim AS base

ARG DEBIAN_FRONTEND=noninteractive

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    MCP_RANDOM_SEED=1234

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN useradd --create-home --shell /bin/bash appuser

ENV HOME=/home/appuser
WORKDIR /app

##########################################
# 3. Builder phase
FROM base AS builder

COPY --from=uv /uv /usr/local/bin/uv
RUN chmod +x /usr/local/bin/uv

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential git \
    && rm -rf /var/lib/apt/lists/*

ENV VIRTUAL_ENV=/opt/venv \
    UV_PROJECT_ENVIRONMENT=${VIRTUAL_ENV}

RUN uv venv --python 3.12 "${VIRTUAL_ENV}"

COPY pyproject.toml uv.lock README.md ./
COPY plugins ./plugins
COPY examples ./examples
COPY docker/entrypoint.sh ./docker/entrypoint.sh

RUN uv sync --frozen --all-packages \
    && uv pip install -r pyproject.toml \
    && chmod +x docker/entrypoint.sh

RUN test -x ${VIRTUAL_ENV}/bin/hopeit_mcp_server

##########################################
# 4. Runner: slim runtime + prebuilt venv
FROM base AS runner

ENV VIRTUAL_ENV=/opt/venv \
    UV_PROJECT_ENVIRONMENT=${VIRTUAL_ENV} \
    MCP_SERVER_PORT=8765

COPY --from=builder --chown=appuser:appuser ${VIRTUAL_ENV} ${VIRTUAL_ENV}
COPY --from=builder --chown=appuser:appuser /app /app

USER appuser
WORKDIR /app
ENV PATH="${VIRTUAL_ENV}/bin:${PATH}"

EXPOSE ${MCP_SERVER_PORT}

ENTRYPOINT ["./docker/entrypoint.sh"]
CMD ["run", "--transport", "stdio", "--host", "0.0.0.0", "--port", "8765", "--config-files", "plugins/mcp/mcp-server/config/dev-noauth-docker.json,plugins/mcp/mcp-server/config/plugin-config.json,examples/plugins/example-tool/config/plugin-config.json"]
