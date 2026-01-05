source := ${wildcard ./arxiv/*.py}
tests := ${wildcard tests/*.py}

# UV-based development workflow (assumes UV is installed)
.PHONY: all install install-dev lint format test audit docs clean sync lock help

# Default target
all: lint test docs

# Installation and dependency management
install:
	@echo "📦 Installing package with UV..."
	uv sync

install-dev:
	@echo "🔧 Installing development dependencies with UV..."
	uv sync --group dev

sync:
	@echo "🔄 Syncing dependencies..."
	uv sync --group dev

lock:
	@echo "🔒 Updating lockfile..."
	uv lock

# Development tasks
format: $(source) $(tests)
	@echo "✨ Formatting code..."
	uv run ruff format .

lint: $(source) $(tests)
	@echo "🔍 Linting code..."
	uv run ruff check .

test: $(source) $(tests)
	@echo "🧪 Running tests..."
	uv run pytest

audit:
	@echo "🔒 Auditing dependencies..."
	uv run pip-audit

docs: docs/index.html
docs/index.html: $(source) README.md
	@echo "📖 Generating documentation..."
	uv run pdoc --docformat "restructuredtext" ./arxiv/__init__.py -o docs

clean:
	@echo "🧹 Cleaning build artifacts..."
	rm -rf build dist .pytest_cache
	rm -rf __pycache__ **/__pycache__
	rm -rf *.pyc **/*.pyc
	rm -rf arxiv.egg-info arxiv/_version.py
	uv cache clean

# Convenience commands
check: lint test
	@echo "✅ All checks passed!"

dev-setup: install-dev
	@echo "🚀 Development environment ready!"
	@echo "💡 Available commands: make lint, make test, make format"

# Show available commands
help:
	@echo "📋 Available commands:"
	@echo "  make install      - Install package dependencies"
	@echo "  make install-dev  - Install with dev dependencies" 
	@echo "  make sync         - Sync all dependencies"
	@echo "  make lock         - Update lockfile"
	@echo "  make test         - Run tests"
	@echo "  make lint         - Run linting"
	@echo "  make format       - Format code"
	@echo "  make docs         - Generate documentation"
	@echo "  make audit        - Security audit"
	@echo "  make check        - Run lint + test"
	@echo "  make clean        - Clean build artifacts"
	@echo "  make dev-setup    - Set up development environment"
	@echo ""
	@echo "🔧 This Makefile uses UV for development workflow"
	@echo "💡 Install UV: curl -LsSf https://astral.sh/uv/install.sh | sh"
	@echo "📚 End users can still use: pip install arxiv"

# Release and distribution
build:
	@echo "📦 Building distributions..."
	uv build

release:
	@echo "🚀 Use the release script for safer releases:"
	@echo "  ./release.sh <version>        # Full release"
	@echo "  ./release.sh <version> --dry-run  # Test release process"
	@echo ""
	@echo "Example: ./release.sh 2.4.0"

version:
	@echo "📝 Current version info:"
	uv run python -c "import arxiv; print(f'Package version: {getattr(arxiv, \"__version__\", \"Unknown\")}')"
	@git describe --tags --always --dirty 2>/dev/null || echo "No git tags found"
