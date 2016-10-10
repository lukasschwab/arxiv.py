# -*- coding: utf-8 -*-

"""A Python wrapper for the arXiv API."""

from __future__ import absolute_import, division, print_function

import os

from setuptools import find_packages, setup


g = {}
with open(os.path.join('arxiv', 'version.py'), 'rt') as f:
    exec(f.read(), g)
    version = g['__version__']

readme = open('README.md').read()
history = open('CHANGES.md').read()

packages = find_packages()

install_requires = [
    'click>=6.6',
    'feedparser>=5.2.1',
    'requests>=2.11.1',
]

setup_requires = [
    'pytest-runner>=2.9',
]

docs_require = []

tests_require = [
    'pytest>=3.0.3',
    'pytest-cov>=2.3.1',
    'pytest-pep8>=1.0.6',
]

extras_require = {
    'docs': docs_require,
    'tests': tests_require,
}

extras_require['all'] = []
for reqs in extras_require.values():
    extras_require['all'].extend(reqs)

setup(
    name='arxiv',
    version=version,
    description=__doc__,
    long_description=readme + '\n\n' + history,
    keywords='arxiv api wrapper',
    license='MIT',
    author='Lukas Schwab',
    author_email='lukas.schwab@gmail.com',
    url='https://github.com/lukasschwab/arxiv.py',
    packages=packages,
    zip_safe=False,
    include_package_data=True,
    platforms='any',
    entry_points={
        'console_scripts': [
            'arxiv = arxiv.cli:cli',
        ],
    },
    install_requires=install_requires,
    setup_requires=setup_requires,
    tests_require=tests_require,
    extras_require=extras_require,
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Topic :: Scientific/Engineering :: Information Analysis',
        'Topic :: Software Development :: Libraries',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: Utilities',
    ],
)
