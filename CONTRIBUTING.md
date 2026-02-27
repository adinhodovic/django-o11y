# Contributing to django-o11y

## Development setup

### Prerequisites

- Python 3.12 or later
- [uv](https://github.com/astral-sh/uv)
- Docker and Docker Compose

### Installation

```bash
git clone https://github.com/adinhodovic/django-o11y.git
cd django-o11y
uv sync --all-extras
```

### Project structure

```text
django-o11y/
├── src/django_o11y/        # The library
│   ├── apps.py             # AppConfig — all wiring happens in ready()
│   ├── config/setup.py     # Configuration: defaults → DJANGO_O11Y dict → env vars
│   ├── logging/            # Structured logging (structlog)
│   ├── tracing/            # OpenTelemetry tracing
│   ├── metrics/            # Prometheus metrics
│   ├── profiling/          # Pyroscope profiling
│   ├── celery/             # Celery instrumentation
│   └── management/commands/  # o11y CLI (stack start/stop, check)
│
├── tests/                  # Embedded Django project used for tests and local dev
│   ├── config/settings/
│   │   ├── test.py         # Used by tox — no real broker, no LOGGING wiring
│   │   └── dev.py          # Used by Docker Compose — JSON logs, real Redis
│   ├── conftest.py         # Shared fixtures, make_config() helper
│   └── Dockerfile          # Multi-stage uv build for dev containers
│
├── docker-compose.dev.yml  # Local dev stack (Django + Celery + Redis + task generator)
├── Makefile                # Shortcuts: make dev, make o11y-stack, etc.
└── docs/                   # Usage and configuration guides
```

## Running tests

Always use tox, not bare pytest:

```bash
# Single environment (fast)
tox -e py312-django52

# Full matrix (Django 5.2 + 6.0, Python 3.12 + 3.13)
tox

# Integration tests (requires observability stack — see below)
tox -e integration
```

## Linting

Always use tox, not ruff or pylint directly:

```bash
tox -e ruff     # ruff lint + format check
tox -e pylint   # pylint
```

## Local dev with Docker Compose

`make dev` starts a full local environment with Django, a Celery worker, Redis,
and a task-generator that hits `/trigger/` every five seconds:

```bash
make dev          # build and start (docker compose up --build)
make dev-stop     # tear down
make dev-logs     # follow logs
```

The Django process listens on `http://localhost:8000`. The Celery worker metrics
server listens on `http://localhost:8009/metrics`. Both use
`tests/config/settings/dev.py`, which wires up JSON structured logging, a real
Redis broker, and tracing pointed at `host.docker.internal:4317`.

To see traces and logs you need the observability stack running as well (see below).

## Observability stack

`make o11y-stack` starts Grafana, Tempo, Loki, Prometheus, Pyroscope, and Alloy:

```bash
make o11y-stack           # start
make o11y-stack-stop      # stop
make o11y-stack-logs      # follow logs
```

After it's up, verify everything is reachable:

```bash
python manage.py o11y check
```

Then open Grafana at `http://localhost:3000` to explore traces, logs, and metrics.

Run both stacks together for a full local observability loop:

```bash
make o11y-stack
make dev
```

## Pre-commit checklist

Before opening a PR:

1. Tests pass: `tox -e py312-django52`
2. Lint clean: `tox -e ruff && tox -e pylint`
3. Integration tests pass if you changed signal handlers or Celery setup: `tox -e integration`

## Need help?

- Questions: open a [Discussion](https://github.com/adinhodovic/django-o11y/discussions)
- Bug report: open an [Issue](https://github.com/adinhodovic/django-o11y/issues)
- Feature request: open an [Issue](https://github.com/adinhodovic/django-o11y/issues) with the `enhancement` label

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
