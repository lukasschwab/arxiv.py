source := ${wildcard ./arxiv/*.py}
tests := ${wildcard tests/*.py}

.PHONY: all install install-dev lint format type-check test audit docs clean check

# Default target
all: lint test docs

# Installation and dependency management
install:
	uv sync --locked --no-default-groups

install-dev:
	uv sync --locked

# Development tasks
format: $(source) $(tests)
	uv run --locked --no-default-groups --group lint ruff format .

lint: $(source) $(tests)
	uv run --locked --no-default-groups --group lint ruff check .

type-check: $(source)
	uv run --locked --no-default-groups --group lint mypy arxiv

test: $(source) $(tests)
	uv run --locked --no-default-groups --group test pytest

audit:
	uv sync --locked --no-default-groups --group audit
	@requirements=$$(mktemp); trap 'rm -f "$$requirements"' EXIT; \
		uv export --locked --all-groups --no-emit-project --format requirements.txt \
			--output-file "$$requirements" > /dev/null && \
		uv run --no-sync pip-audit --strict --disable-pip --require-hashes \
			--requirement "$$requirements"

docs: docs/index.html
docs/index.html: $(source) README.md
	uv run --locked --no-default-groups --group docs pdoc --docformat "restructuredtext" ./arxiv/__init__.py '!arxiv._feed' -o docs

clean:
	rm -rf build dist .pytest_cache
	rm -rf __pycache__ **/__pycache__
	rm -rf *.pyc **/*.pyc
	rm -rf arxiv.egg-info arxiv/_version.py

# Convenience commands
check: lint type-check test

