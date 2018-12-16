from setuptools import setup

version = "0.3.0"

setup(
	name="arxiv",
	version=version,
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
	download_url="https://github.com/lukasschwab/arxiv.py/tarball/"+version,
    classifiers=[
        "Programming Language :: Python",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
