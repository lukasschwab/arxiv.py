source := ${wildcard ./arxiv/*.py}
tests := ${wildcard tests/*.py}

.PHONY: all lint test audit docs clean

all: lint test docs

format: $(source) $(tests)
	ruff format .

lint: $(source) $(tests)
	ruff check .

test: $(source) $(tests)
	pytest

audit:
	python -m pip_audit --strict --requirement requirements.txt

docs: docs/index.html
docs/index.html: $(source) README.md
	pdoc --version
	pdoc --docformat "restructuredtext" ./arxiv/__init__.py -o docs

clean:
	rm -rf build dist
	rm -rf __pycache__ **/__pycache__
	rm -rf *.pyc **/*.pyc
	rm -rf arxiv.egg-info
