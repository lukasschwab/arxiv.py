SOURCE := ${wildcard ./arxiv/*.py}
TESTS := ${wildcard tests/*.py}

.PHONY: all test docs

all: test docs

test: *.py
	pytest

docs: $(SOURCE)
	pdoc arxiv -o docs
	mv docs/arxiv/arxiv.html docs/index.html
	rm docs/arxiv.html
	rmdir docs/arxiv