.PHONY: setup dev dev-stop dev-logs o11y-stack o11y-stack-stop o11y-stack-logs docs

setup:
	uv sync --all-extras

dev:
	docker compose up --build --watch

dev-stop:
	docker compose stop

dev-logs:
	docker compose logs -f

o11y-stack:
	python manage.py o11y stack start

o11y-stack-stop:
	python manage.py o11y stack stop

o11y-stack-logs:
	python manage.py o11y stack logs

DOCS_PORT ?= 8001

docs:
	uv run zensical serve -a localhost:$(DOCS_PORT)
