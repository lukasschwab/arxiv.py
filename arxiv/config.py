# -*- coding: utf-8 -*-

"""Initial configuration for this package.

Variable ``FOO`` is overridden by adding to the environment
a variable called ``ARXIV_FOO``.
"""

from __future__ import absolute_import, division, print_function

import os


API_BASE_URL = os.environ.get(
    'ARXIV_API_BASE_URL', 'http://export.arxiv.org/api/query?')

CHUNK_SIZE = os.environ.get('ARXIV_CHUNK_SIZE', 4096)

PDF_BASE_URL = os.environ.get(
    'ARXIV_PDF_BASE_URL', 'http://export.arxiv.org/pdf/')

TIMEOUT = os.environ.get('ARXIV_TIMEOUT', 3)
