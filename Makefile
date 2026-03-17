# =============================================================================
# Harmoni ERP — Makefile
# =============================================================================

.PHONY: test lint deploy run migrate collectstatic celery

test:
	pytest --tb=short -q

lint:
	ruff check .

lint-fix:
	ruff check --fix .

deploy:
	bash deploy/deploy.sh

run:
	python manage.py runserver

migrate:
	python manage.py migrate

collectstatic:
	python manage.py collectstatic --noinput

celery:
	celery -A config worker -l info

celery-beat:
	celery -A config beat -l info
