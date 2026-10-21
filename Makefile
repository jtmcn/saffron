.DEFAULT_GOAL := check
.PHONY: install lint fmt test check backlog deadcode

install:
	uv sync
	prek install

lint:
	status=0; prek run --all-files --skip prose-limit || status=$$?; prek run --all-files --stage manual prose-limit-tree || status=$$?; exit $$status

fmt:
	uv run ruff check --fix .
	uv run ruff format .

test:
	uv run pytest

check: lint test

backlog:
	uv run python -m records list backlog

deadcode:
	uv run python .saffron/gates/dead.py --report
