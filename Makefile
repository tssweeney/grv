.PHONY: test lint format typecheck check-loc check-unused check-all ci

test:
	uv run pytest

lint:
	uv run ruff check .

format:
	uv run ruff format .

format-check:
	uv run ruff format --check .

typecheck:
	uv run mypy src/grv

check-loc:
	uv run python scripts/check_loc.py

check-unused:
	uv run vulture src/grv --min-confidence 80

check-all: format-check lint typecheck check-loc check-unused test

ci: check-all
