source := ${wildcard ./arxiv/*.py}
tests := ${wildcard tests/*.py}

.PHONY: all lint lint-ci test docs clean

all: lint test docs

lint: $(source) $(tests)
	flake8 .

lint-ci: $(source) $(tests)
	# stop the build if there are Python syntax errors or undefined names.
	flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
	# exit-zero treats all errors as warnings. Warn about complexity.
	flake8 . --count --exit-zero --max-complexity=10 --statistics

test: $(source) $(tests)
	pytest

docs: $(source)
	pdoc arxiv -o docs
	mv docs/arxiv/arxiv.html docs/index.html
	rm docs/arxiv.html
	rmdir docs/arxiv

clean:
	rm -rf build dist
	rm -rf __pycache__ **/__pycache__
	rm -rf *.pyc **/*.pyc
	rm -rf arxiv.egg-info