SOURCE := ${wildcard ./arxiv/*.py}
TESTS := ${wildcard tests/*.py}

.PHONY: all test docs clean

all: lint test docs

lint:
	flake8 $(SOURCE) $(TESTS) --ignore=E501

test: $(SOURCE) $(TESTS)
	pytest

docs: $(SOURCE)
	pdoc arxiv -o docs
	mv docs/arxiv/arxiv.html docs/index.html
	rm docs/arxiv.html
	rmdir docs/arxiv

clean:
	rm -rf build dist
	rm -rf __pycache__ **/__pycache__
	rm -rf *.pyc **/*.pyc
	rm -rf arxiv.egg-info