# syntax=docker/dockerfile:1

##########################################
# 1. Gets uv for the building platform
FROM ghcr.io/astral-sh/uv:latest AS uv

##########################################
# 2. Base operating system with non-root user
FROM ubuntu:latest AS base

RUN useradd --create-home --shell /bin/bash appuser

ENV HOME=/home/appuser
WORKDIR /app

##########################################
# 3. Builder phase
FROM base AS builder

COPY --from=uv /uv /usr/local/bin/uv
RUN chmod +x /usr/local/bin/uv

ENV VIRTUAL_ENV=/opt/venv
ENV UV_PROJECT_ENVIRONMENT=${VIRTUAL_ENV}

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

ENV VIRTUAL_ENV=/opt/venv

COPY --from=builder --chown=root:appuser --chmod=050 /home/appuser/.local/share/uv/python/ /home/appuser/.local/share/uv/python/
COPY --from=builder --chown=appuser:appuser ${VIRTUAL_ENV} ${VIRTUAL_ENV}
COPY --from=builder --chown=appuser:appuser /app /app

USER appuser
WORKDIR /app
ENV PATH="${VIRTUAL_ENV}/bin:${PATH}"

ENTRYPOINT ["hopeit_mcp_server", "run"]
CMD ["--transport", "stdio", "--config-files", "plugins/mcp/mcp-server/config/dev-noauth-docker.json,plugins/mcp/mcp-server/config/plugin-config.json,examples/plugins/example-tool/config/plugin-config.json"]
