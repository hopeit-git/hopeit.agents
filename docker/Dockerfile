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

RUN uv sync --frozen --no-dev

RUN test -x ${VIRTUAL_ENV}/bin/hopeit_server

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

ENTRYPOINT ["hopeit_server", "run"]
CMD ["--host", "0.0.0.0", "--port", "8020", "--path", "work", "--config-files", "examples/apps/example-agents/config/dev-noauth.json,examples/apps/example-agents/config/app-config.json"]
