.PHONY: help test lint typecheck format migrate deploy clean

help:
	@echo "Available targets:"
	@echo "  test       - run tests"
	@echo "  lint       - run ruff"
	@echo "  typecheck  - run mypy"
	@echo "  format     - format code with ruff"
	@echo "  migrate    - generate alembic migration"
	@echo "  deploy     - build and push Docker image"
	@echo "  clean      - remove caches and build artifacts"

test:
	pytest

lint:
	ruff check .

typecheck:
	mypy src/ tests/ --ignore-missing-imports

format:
	ruff format .

migrate:
	alembic revision --autogenerate -m "$(msg)"

deploy:
	docker build -t botkit-reminder:latest .
	docker tag botkit-reminder:latest registry.example.com/botkit-reminder:latest
	docker push registry.example.com/botkit-reminder:latest

clean:
	rm -rf .pytest_cache .mypy_cache .ruff_cache .hypothesis .coverage htmlcov __pycache__ *.pyc
