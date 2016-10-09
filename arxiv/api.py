# -*- coding: utf-8 -*-

"""API offered by this package."""

from __future__ import absolute_import, division, print_function

from feedparser import parse
from requests import get, post

from .config import API_BASE_URL, CHUNK_SIZE, PDF_BASE_URL, TIMEOUT
from .core import _build_filename, _build_query, _get_id
from .errors import ArxivAPIError
from .utils import has, drip


class Client(object):

    def __init__(self):
        self._cache = {}

    def download(self, id_list, **kwargs):
        def _download(id_):
            response = get(PDF_BASE_URL + id_, stream=True)
            with open(_build_filename(id_), 'wb') as f:
                for chunk in response.iter_content(chunk_size=CHUNK_SIZE):
                    if chunk:
                        f.write(chunk)

        timeout = TIMEOUT
        if has(kwargs, 'timeout'):
            timeout = int(kwargs['timeout'])

        drip(_download, id_list, t=timeout)

    def fetch(self, id_list, **kwargs):
        response = self._query(id_list=id_list)
        parsed_response = parse(response)

        return parsed_response

    def find(self, search_query, **kwargs):
        response = self._query(search_query=search_query)
        parsed_response = parse(response)

        if has(kwargs, 'ids') and kwargs['ids']:
            return ' '.join(map(_get_id, parsed_response['entries']))

        return parsed_response

    def _query(self, **kwargs):
        query = _build_query(**kwargs)
        if query in self._cache:
            return self._cache(query)

        response = post(API_BASE_URL, data=query)
        if not response.ok:
            raise ArxivAPIError(response.reason)

        self._cache[query] = response.content
        return self._cache[query]
