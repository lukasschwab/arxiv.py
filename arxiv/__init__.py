# -*- coding: utf-8 -*-

"""A Python wrapper for the arXiv API."""

from __future__ import absolute_import, division, print_function

from .api import Client
from .version import __version__


__all__ = (
    'Client',
    '__version__',
)
