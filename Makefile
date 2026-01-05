source := ${wildcard ./arxiv/*.py}
tests := ${wildcard tests/*.py}

# UV-based development workflow (assumes UV is installed)
.PHONY: all install install-dev lint format test audit docs clean sync lock help

# Default target
all: lint test docs

# Installation and dependency management
install:
	uv sync

install-dev:
	uv sync --group dev

sync:
	uv sync --group dev

lock:
	uv lock

# Development tasks
format: $(source) $(tests)
	uv run ruff format .

lint: $(source) $(tests)
	uv run ruff check .

type-check: $(source)
	uv run mypy arxiv/__init__.py

test: $(source) $(tests)
	uv run pytest

audit:
	uv run pip-audit

docs: docs/index.html
docs/index.html: $(source) README.md
	uv run pdoc --docformat "restructuredtext" ./arxiv/__init__.py -o docs

clean:
	rm -rf build dist .pytest_cache
	rm -rf __pycache__ **/__pycache__
	rm -rf *.pyc **/*.pyc
	rm -rf arxiv.egg-info arxiv/_version.py
	uv cache clean

# Convenience commands
check: lint type-check test

# Release and distribution
build:
	uv build

release:
	./release.sh
