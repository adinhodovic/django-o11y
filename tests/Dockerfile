# syntax=docker/dockerfile:1.9
FROM python:3.12-slim AS build

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ENV UV_LINK_MODE=copy \
  UV_COMPILE_BYTECODE=1 \
  UV_PROJECT_ENVIRONMENT=/app \
  UV_NO_DEV=1

# Install dependencies first (separate from app code for better caching)
RUN --mount=type=cache,target=/root/.cache \
  --mount=type=bind,source=uv.lock,target=uv.lock \
  --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
  uv sync --locked --no-install-project --extra all

# Now install the application itself
COPY . /src
WORKDIR /src
RUN --mount=type=cache,target=/root/.cache \
  uv sync --locked --no-editable --extra all

##########################################################################

FROM python:3.12-slim

ENV PATH=/app/bin:$PATH \
  PYTHONUNBUFFERED=1 \
  DJANGO_O11Y_METRICS_MULTIPROC_BASE_DIR=/tmp/django-wtf-prom-multiproc \
  PROMETHEUS_MULTIPROC_DIR=/tmp/django-wtf-prom-multiproc

COPY --from=build /app /app
COPY --from=build /src /app

WORKDIR /app
