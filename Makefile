source := ${wildcard ./arxiv/*.py}
tests := ${wildcard tests/*.py}

.PHONY: all install install-dev lint format type-check test audit docs clean check

# Default target
all: lint test docs

# Installation and dependency management
install:
	uv sync --locked --no-dev

install-dev:
	uv sync --locked

# Development tasks
format: $(source) $(tests)
	uv run --locked ruff format .

lint: $(source) $(tests)
	uv run --locked ruff check .

type-check: $(source)
	uv run --locked ty check arxiv

test: $(source) $(tests)
	uv run --locked pytest

audit:
	uv sync --locked
	@requirements=$$(mktemp); trap 'rm -f "$$requirements"' EXIT; \
		uv export --locked --no-emit-project --format requirements.txt \
			--output-file "$$requirements" > /dev/null && \
		uv run --no-sync pip-audit --strict --disable-pip --require-hashes \
			--requirement "$$requirements"

docs: docs/index.html
docs/index.html: $(source) README.md
	uv run --locked pdoc --docformat "restructuredtext" ./arxiv/__init__.py '!arxiv._feed' -o docs

clean:
	rm -rf build dist .pytest_cache
	rm -rf __pycache__ **/__pycache__
	rm -rf *.pyc **/*.pyc
	rm -rf arxiv.egg-info arxiv/_version.py

# Convenience commands
check: lint type-check test

