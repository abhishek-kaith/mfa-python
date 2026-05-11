.PHONY: install run test lint fmt migrate shell keys clean help

help:           ## show available targets
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "%-12s %s\n", $$1, $$2}'

install:        ## install deps with uv
	uv sync

run:            ## start dev stack
	docker compose up --build

test:           ## run pytest inside web container
	docker compose exec web pytest

lint:           ## ruff check
	uv run ruff check .

fmt:            ## ruff format
	uv run ruff format .

migrate:        ## run migrations inside web container
	docker compose exec web python manage.py migrate

shell:          ## django shell in container
	docker compose exec web python manage.py shell

keys:           ## generate fresh SECRET_KEY and FERNET_KEY
	uv run python scripts/generate_keys.py

demo-users:     ## create three demo users for graders
	docker compose exec web python manage.py create_demo_users

clean:          ## tear down stack and remove volumes
	docker compose down -v
