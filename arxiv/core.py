# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, print_function

from urllib import urlencode

from .utils import has


def _build_filename(id_):
    return '{}.pdf'.format(id_.replace('/', '-'))


def _build_query(**kwargs):
    result = []

    if has(kwargs, 'search_query'):
        result.append(('search_query', kwargs['search_query']))

    if has(kwargs, 'id_list'):
        result.append(('id_list', ','.join(kwargs['id_list'])))

    if has(kwargs, 'start'):
        result.append(('start', kwargs['start']))

    if has(kwargs, 'max_results'):
        result.append(('max_results', kwargs['max_results']))

    if has(kwargs, 'sort_by'):
        result.append(('sortBy', kwargs['sort_by']))

    if has(kwargs, 'sort_order'):
        result.append(('sortOrder', kwargs['sort_order']))

    return urlencode(result)


def _get_id(entry):
    return entry['id'][21:]
