source := ${wildcard ./arxiv/*.py}
tests := ${wildcard tests/*.py}

.PHONY: all lint test docs clean

all: lint test docs

lint: $(source) $(tests)
	flake8 . --count --max-complexity=10 --statistics

test: $(source) $(tests)
	pytest

docs: docs/index.html
docs/index.html: $(source)
	pdoc ./arxiv -o docs
	mv docs/arxiv/arxiv.html docs/index.html
	rm docs/arxiv.html
	rmdir docs/arxiv

clean:
	rm -rf build dist
	rm -rf __pycache__ **/__pycache__
	rm -rf *.pyc **/*.pyc
	rm -rf arxiv.egg-info
