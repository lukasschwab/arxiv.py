from setuptools import setup

setup(
	name="arxiv",
	version="0.2.2",
	packages=["arxiv"],

	# dependencies
	install_requires=[
		'feedparser',
		'requests',
	],

	# metadata for upload to PyPI
	author="Lukas Schwab",
	author_email="lukas.schwab@gmail.com",
	description="Python wrapper for the arXiv API: http://arxiv.org/help/api/",
	license="MIT",
	keywords="arxiv api wrapper academic journals papers",
	url="https://github.com/lukasschwab/arxiv.py",
	download_url="https://github.com/lukasschwab/arxiv.py/tarball/0.2.2",
)
