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
	DJANGO_SETTINGS_MODULE=tests.config.settings.local CELERY_BROKER_URL=$${CELERY_BROKER_URL:-redis://localhost:6379/0} DJANGO_O11Y_LOGGING_FILE_ENABLED=false python manage.py o11y stack start

o11y-stack-stop:
	python manage.py o11y stack stop

o11y-stack-logs:
	python manage.py o11y stack logs
