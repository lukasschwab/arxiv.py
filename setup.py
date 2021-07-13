from setuptools import setup

version = '1.4.0'

with open('README.md', 'r') as fh:
    long_description = fh.read()

setup(
    name='arxiv',
    version=version,
    packages=['arxiv'],
    # dependencies
    install_requires=['feedparser'],
    tests_require=[
        'pytest',
        'pdoc',
        'flake8'
    ],
    # metadata for upload to PyPI
    author='Lukas Schwab',
    author_email='lukas.schwab@gmail.com',
    description='Python wrapper for the arXiv API: http://arxiv.org/help/api/',
    long_description=long_description,
    long_description_content_type='text/markdown',
    license='MIT',
    keywords='arxiv api wrapper academic journals papers',
    url='https://github.com/lukasschwab/arxiv.py',
    classifiers=[
        'Programming Language :: Python',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
)
