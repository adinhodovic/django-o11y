.PHONY: dev dev-stop dev-logs o11y-stack o11y-stack-stop o11y-stack-logs

dev:
	docker compose -f docker-compose.dev.yml up --build --watch

dev-stop:
	docker compose -f docker-compose.dev.yml stop

dev-logs:
	docker compose -f docker-compose.dev.yml logs -f

o11y-stack:
	python manage.py o11y stack start

o11y-stack-stop:
	python manage.py o11y stack stop

o11y-stack-logs:
	python manage.py o11y stack logs
