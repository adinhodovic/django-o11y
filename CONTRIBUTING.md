# Contributing to Django Observability

Thanks for contributing to Django Observability.

## Development setup

### Prerequisites

- Python 3.12 or later
- Docker and Docker Compose (for E2E testing with observability stack)
- uv (recommended) or pip

### Installation

```bash
# Clone the repository
git clone https://github.com/adinhodovic/django-observability.git
cd django-observability

# Install all dependencies (including all extras)
uv sync --all-extras
```

### Project structure

```
django-observability/
├── src/django_observability/        # Main package
│   ├── apps.py                      # Django app config
│   ├── conf.py                      # Configuration management
│   ├── context.py                   # Custom tags helper
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

### Test with coverage

```bash
uv run pytest --cov=django_observability --cov-report=term --cov-report=html
```

View coverage report:

```bash
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
```

### Test categories

**Unit tests** - No external dependencies:
```bash
uv run pytest -m "not integration"
```

**Integration tests** - Requires observability stack running:
```bash
# Start stack first
python manage.py observability stack start

# Run integration tests
uv run pytest -m "integration" -v

# Stop stack
python manage.py observability stack stop
```

### Test configuration

Tests use `tests/settings.py` with sane defaults:
- All instrumentation enabled by default (tests should reflect production)
- File-based SQLite database (not :memory:) for manual testing
- Shared fixtures in `tests/conftest.py`

Override via environment variables:
```bash
export LOG_LEVEL=DEBUG
export OTEL_TRACE_SAMPLE_RATE=0.1
pytest tests/
```

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

## Making changes

### Development workflow

1. **Create a feature branch**
   ```bash
   git checkout -b feature/my-new-feature
   ```

2. **Make your changes**
   - Follow existing code patterns
   - Add tests for new functionality
   - Update documentation if needed

3. **Run tests locally**
   ```bash
   uv run pytest
   ```

4. **Commit your changes**
   ```bash
   git add .
   git commit -m "feat: add new feature"
   ```

5. **Push and create a PR**
   ```bash
   git push origin feature/my-new-feature
   ```

### Commit message format

Follow [Conventional Commits](https://www.conventionalcommits.org/):

- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation changes
- `test:` - Test changes
- `refactor:` - Code refactoring
- `chore:` - Maintenance tasks

Examples:
```
feat: add request correlation ID middleware
fix: resolve trace context propagation in celery tasks
docs: update configuration guide with new options
test: add unit tests for custom tags helper
```

## Testing your changes

### Manual testing

Start the observability stack and test manually:

```bash
# Start stack
python manage.py observability stack start

# Run Django dev server (uses tests/ as Django project)
python manage.py runserver

# Generate some traffic
curl http://localhost:8000/

# Check setup
python manage.py observability check

# View in Grafana
open http://localhost:3000

# Stop stack
python manage.py observability stack stop
```

### Testing CLI commands

Test the new Click-based CLI:

```bash
# Show help
python manage.py observability --help
python manage.py observability stack --help
python manage.py observability check --help

# Test commands
python manage.py observability stack start
python manage.py observability stack status
python manage.py observability check
python manage.py observability stack logs --follow
python manage.py observability stack stop
```

## Pull request guidelines

### Before submitting

- [ ] Tests pass locally
- [ ] Code follows project style (ruff format + check)
- [ ] Type hints added for new functions
- [ ] Documentation updated if needed
- [ ] CHANGELOG.md updated (for user-facing changes)

### PR description

Include:
1. **What** - What does this PR do?
2. **Why** - Why is this change needed?
3. **How** - How does it work? (if complex)
4. **Testing** - How did you test it?

## Core concepts (important)

### Hybrid metrics approach

**Don't break this:**
- Use `django-prometheus` for infrastructure metrics (existing blog dashboards work out-of-box)
- Use OpenTelemetry for business metrics with exemplars (click metric → trace)

### Trace correlation

- Logs MUST include `trace_id` and `span_id` (via `add_open_telemetry_spans()` processor)
- Request IDs should propagate across services

## Need help?

- **Questions?** Open a [Discussion](https://github.com/adinhodovic/django-observability/discussions)
- **Bug report?** Open an [Issue](https://github.com/adinhodovic/django-observability/issues)
- **Feature request?** Open an [Issue](https://github.com/adinhodovic/django-observability/issues) with `enhancement` label

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
