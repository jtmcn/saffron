.DEFAULT_GOAL := check
.PHONY: install lint fmt test check

install:
	uv sync
	prek install

lint:
	prek run --all-files

fmt:
	uv run ruff check --fix .
	uv run ruff format .

test:
	uv run pytest

check: lint test
