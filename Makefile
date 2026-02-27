.PHONY: setup dev dev-stop dev-logs o11y-stack o11y-stack-stop o11y-stack-logs

setup:
	uv sync --all-extras

dev:
	docker compose -f docker-compose.dev.yml up --build --watch

dev-stop:
	docker compose -f docker-compose.dev.yml stop

dev-logs:
	docker compose -f docker-compose.dev.yml logs -f

o11y-stack:
	DJANGO_SETTINGS_MODULE=tests.config.settings.local CELERY_BROKER_URL=$${CELERY_BROKER_URL:-redis://localhost:6379/0} DJANGO_O11Y_LOGGING_FILE_ENABLED=false DJANGO_O11Y_DEV_DB_NAME=$$PWD/dev_db.sqlite3 DJANGO_O11Y_STACK_LOG_DIR=$${DJANGO_O11Y_DEV_TMP_DIR:-/tmp/django-o11y-$${COMPOSE_PROJECT_NAME:-django-o11y}} python manage.py o11y stack start

o11y-stack-stop:
	python manage.py o11y stack stop

o11y-stack-logs:
	python manage.py o11y stack logs
