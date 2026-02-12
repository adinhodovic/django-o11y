# Django Observability - Dev Instructions

**Quick Reference**: Comprehensive OpenTelemetry package for Django with tracing, logging, metrics, and profiling.

---

## Core Concepts

**Hybrid Metrics** (Don't break this!)
- django-prometheus for infrastructure metrics (blog dashboards work out-of-box)
- OpenTelemetry for business metrics with exemplars (click metric → trace)

**Zero Config**
- Must work with just adding to INSTALLED_APPS
- Auto-setup via `apps.py` AppConfig

**Trace Correlation**
- Logs must include trace_id/span_id (via `add_open_telemetry_spans()` processor)

---

## Project Structure

```
src/django_observability/           # Main package
├── apps.py                         # Auto-setup entry point
├── conf.py                         # Config (settings + env vars)
├── tracing/provider.py             # OTel TracerProvider
├── logging/
│   ├── config.py                   # Structlog setup (from blog)
│   ├── processors.py               # add_open_telemetry_spans()
│   └── otlp_handler.py            # OTLP log export
├── middleware/
│   ├── tracing.py                  # Request tracing
│   └── logging.py                  # Request logging
├── instrumentation/setup.py        # Auto-instrument Django/DB/cache
├── metrics/custom.py               # counter(), histogram() helpers
└── celery/
    ├── setup.py                    # setup_celery_observability()
    └── signals.py                  # Task lifecycle logging

examples/demo_project/              # Complete demo
├── docker-compose.yml              # 14 services (includes celery-exporter)
├── demo/
│   ├── settings.py                 # Full config example
│   ├── celery_app.py              # Celery integration
│   └── api/                       # Demo endpoints + tasks
├── alloy/config.alloy             # Metrics + profile scraping
├── grafana/dashboards/             # 5 pre-configured dashboards
│   ├── django-overview.json
│   ├── django-requests-overview.json
│   ├── django-requests-by-view.json
│   ├── celery-tasks-overview.json
│   └── celery-tasks-by-task.json
└── prometheus/prometheus.yml      # Remote write receiver
```

---

## Common Tasks

### Add Configuration Option

**File**: `src/django_observability/conf.py`

```python
defaults = {
    "NEW_FEATURE": {
        "ENABLED": _get_bool_env("DJANGO_OBSERVABILITY_NEW_FEATURE", False),
        "OPTION": os.getenv("DJANGO_OBSERVABILITY_NEW_OPTION", "default"),
    }
}
```

Pattern: Defaults + env vars + deep merge

### Add Middleware

**Dir**: `src/django_observability/middleware/`

1. Create file following `tracing.py` pattern
2. Update README installation instructions
3. Add to demo `demo/settings.py` MIDDLEWARE

### Add Custom Metrics

```python
from django_observability.metrics import counter, histogram

my_counter = counter("my.metric", "Description")
my_counter.add(1, {"label": "value"})

my_histogram = histogram("my.duration", "s")
with my_histogram.time({"op": "process"}):
    # work here
```

### Add Instrumentation

**File**: `src/django_observability/instrumentation/setup.py`

```python
def _instrument_new_library():
    try:
        from opentelemetry.instrumentation.newlib import NewLibInstrumentor
        NewLibInstrumentor().instrument()
    except ImportError:
        pass  # Graceful degradation
```

### Update Demo

- **Endpoint**: `examples/demo_project/demo/api/views.py`
- **Task**: `examples/demo_project/demo/api/tasks.py`
- **Stack**: `examples/demo_project/docker-compose.yml`

---

## Development

### Local Testing

```bash
# Install
uv sync --all-extras

# Tests
uv run pytest

# Lint
uv run ruff check .
uv run ruff format .

# Type check
uv run mypy src/django_observability

# Full matrix
uv run tox
```

### Demo Testing

```bash
cd examples/demo_project

# Start (auto-runs migrations, creates admin/admin, generates data)
docker-compose up -d

# Watch logs
docker-compose logs -f web

# Generate traffic
curl http://localhost:8000/api/simulate-load/

# Access Grafana
open http://localhost:3000

# Cleanup
docker-compose down -v
```

### Before Committing

- [ ] Tests pass: `uv run pytest`
- [ ] Lint passes: `uv run ruff check .`
- [ ] Demo works: `cd examples/demo_project && docker-compose up -d`
- [ ] Conventional commit message (feat:, fix:, docs:, etc.)

---

## Configuration

### Environment Variables

```bash
OTEL_SERVICE_NAME=my-app
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
OTEL_TRACES_SAMPLER_ARG=1.0
DJANGO_LOG_LEVEL=INFO
DJANGO_LOG_FORMAT=json
```

### Django Settings

```python
DJANGO_OBSERVABILITY = {
    'SERVICE_NAME': 'my-app',
    'TRACING': {'ENABLED': True, 'SAMPLE_RATE': 1.0},
    'LOGGING': {'FORMAT': 'json', 'OTLP_ENABLED': True},
    'METRICS': {'PROMETHEUS_ENABLED': True, 'OTLP_ENABLED': True},
    'CELERY': {'ENABLED': True},
}
```

---

## Target Versions

- Python: 3.12, 3.13
- Django: 5.2, 6.0

---

## References

### Blog Posts (Source)
- [Django Monitoring](https://hodovi.cc/blog/django-monitoring-with-prometheus-and-grafana/)
- [Django Logging](https://hodovi.cc/blog/django-development-and-production-logging/)
- [Celery Monitoring](https://hodovi.cc/blog/celery-monitoring-with-prometheus-and-grafana/)

### Related Structure
- `../dj-tailwind` - Package structure reference
