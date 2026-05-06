PYTHON ?= python3
VENV   ?= .venv
VENV_PYTHON := $(VENV)/bin/python
VENV_PIP    := $(VENV)/bin/pip

.PHONY: help venv install lint typecheck test coverage check run clean

help:
	@printf "Targets:\n"
	@printf "  make venv      Create the local virtual environment\n"
	@printf "  make install   Install package and dev dependencies\n"
	@printf "  make lint      Run Ruff lint checks\n"
	@printf "  make typecheck Run mypy type checks\n"
	@printf "  make test      Run unit tests\n"
	@printf "  make coverage  Run tests with coverage report\n"
	@printf "  make check     Run lint, typecheck, and tests\n"
	@printf "  make run       Start the MCP server\n"
	@printf "  make clean     Remove caches and build artifacts\n"

venv:
	$(PYTHON) -m venv $(VENV)

install: venv
	$(VENV_PIP) install -e ".[dev]"

lint:
	$(VENV_PYTHON) -m ruff check src tests

typecheck:
	$(VENV_PYTHON) -m mypy

test:
	$(VENV_PYTHON) -m pytest -q

coverage:
	$(VENV_PYTHON) -m coverage run -m pytest -q
	$(VENV_PYTHON) -m coverage report -m

check: lint typecheck test

run:
	$(VENV_PYTHON) -m asf_policy_mcp.server

clean:
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
	find . -type d -name .pytest_cache -prune -exec rm -rf {} +
	rm -rf .cache build dist *.egg-info src/*.egg-info
