.DEFAULT_GOAL := check
.PHONY: install lint fmt test check

install:
	uv sync
	prek install

lint:
	prek run --all-files

fmt:
	ruff check --fix .
	ruff format .

test:
	uv run pytest

check: lint test
