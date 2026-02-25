# Contributing to django-o11y

Thanks for contributing to django-o11y.

## Development setup

### Prerequisites

- Python 3.12 or later
- Docker and Docker Compose (for E2E testing with observability stack)
- uv (recommended) or pip

### Installation

```bash
# Clone the repository
git clone https://github.com/adinhodovic/django-o11y.git
cd django-o11y

# Install all dependencies (including all extras)
uv sync --all-extras
```

### Project structure

```text
django-o11y/
├── src/django_o11y/        # Main package
│   ├── apps.py                      # Django app config
│   ├── config/setup.py              # Configuration management
│   ├── logging/utils.py             # Logging helper utilities
│   ├── tracing/utils.py             # Trace context helper utilities
│   ├── middleware/                  # Tracing, Logging, Correlation middleware
│   ├── tracing/                     # OpenTelemetry tracing
│   ├── logging/                     # Structured logging
│   ├── metrics/                     # Prometheus metrics
│   ├── profiling/                   # Pyroscope profiling
│   ├── celery/                      # Celery instrumentation
│   └── management/commands/         # Django management commands
│       └── observability.py         # Unified CLI command
│
├── tests/                           # Test Django project
│   ├── settings.py                  # Django settings for tests
│   ├── conftest.py                  # Shared pytest fixtures
│   ├── test_*.py                    # All test files
│   └── models.py                    # Test models
│
└── docs/                            # Documentation (guides & examples)
```

## Running tests

### Quick test

Run all tests:

```bash
uv run pytest
```

### Test categories

**Unit tests** - No external dependencies:

```bash
uv run pytest -m "not integration"
```

**Integration tests** - Requires observability stack running:

```bash
# Start stack first
python manage.py o11y stack start

# Run integration tests
uv run pytest -m "integration" -v

# Stop stack
python manage.py o11y stack stop
```

### Test configuration

Tests use `tests/settings.py` with sane defaults:

- All instrumentation enabled by default (tests should reflect production)
- File-based SQLite database (not :memory:) for manual testing
- Shared fixtures in `tests/conftest.py`

## Code style

### Formatting and linting

```bash
# Format code
ruff format .

# Lint
ruff check . --fix

# Type checking
mypy src/
```

### Pre-commit checks

Before committing, ensure:

1. All tests pass: `uv run pytest`
2. Code is formatted: `uv run ruff format .`
3. No linting errors: `uv run ruff check .`
4. Type checking passes: `uv run mypy src/`

## Testing your changes

### Manual testing

Start the observability stack and test manually:

```bash
# Start stack
python manage.py o11y stack start

# Run Django dev server (uses tests/ as Django project)
python manage.py runserver

# Generate some traffic
curl http://localhost:8000/

# Check setup
python manage.py o11y check

# View in Grafana
open http://localhost:3000

# Stop stack
python manage.py o11y stack stop
```

### Testing CLI commands

Test the new Click-based CLI:

```bash
# Show help
python manage.py o11y --help
python manage.py o11y stack --help
python manage.py o11y check --help

# Test commands
python manage.py o11y stack start
python manage.py o11y stack status
python manage.py o11y check
python manage.py o11y stack logs --follow
python manage.py o11y stack stop
```

## Need help?

- **Questions?** Open a [Discussion](https://github.com/adinhodovic/django-o11y/discussions)
- **Bug report?** Open an [Issue](https://github.com/adinhodovic/django-o11y/issues)
- **Feature request?** Open an [Issue](https://github.com/adinhodovic/django-o11y/issues) with `enhancement` label

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
