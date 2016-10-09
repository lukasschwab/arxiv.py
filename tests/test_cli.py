# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, print_function

import os
import pkg_resources

import httpretty
import pytest

from arxiv.cli import cli
from arxiv.config import API_BASE_URL, PDF_BASE_URL


@pytest.mark.httpretty
def test_download_one_id(runner):
    body = pkg_resources.resource_string(
        __name__, os.path.join('fixtures', '1111.2011v2.pdf'))
    httpretty.register_uri(
        httpretty.GET, PDF_BASE_URL + '1111.2011v2', body=body)

    result = runner.invoke(cli, ['download', '1111.2011v2'])

    assert result.exit_code == 0

    os.remove('1111.2011v2.pdf')


@pytest.mark.httpretty
def test_download_multiple_ids(runner):
    pass


@pytest.mark.httpretty
def test_download_supports_t_and_timeout(runner):
    pass


@pytest.mark.httpretty
def test_fetch_one_id(runner):
    body = pkg_resources.resource_string(
        __name__, os.path.join('fixtures', 'id_list=1111.2011v2.xml'))
    httpretty.register_uri(httpretty.POST, API_BASE_URL, body=body)

    result = runner.invoke(cli, ['fetch', '1111.2011v2'])

    assert result.exit_code == 0


@pytest.mark.httpretty
def test_fetch_multiple_ids(runner):
    pass


@pytest.mark.httpretty
def test_fetch_supports_t_and_timeout(runner):
    pass


@pytest.mark.httpretty
def test_find_search_query(runner):
    body = pkg_resources.resource_string(
        __name__, os.path.join('fixtures', 'search_query=au:del_maestro.xml'))
    httpretty.register_uri(httpretty.POST, API_BASE_URL, body=body)

    result = runner.invoke(cli, ['find', 'au:del_maestro'])

    assert result.exit_code == 0


@pytest.mark.httpretty
def test_find_search_query_supports_booleans(runner):
    body = pkg_resources.resource_string(
        __name__, os.path.join(
            'fixtures', 'search_query=au:del_maestro+AND+ti:checkerboard.xml'))
    httpretty.register_uri(httpretty.POST, API_BASE_URL, body=body)

    result = runner.invoke(cli, [
        'find', '"au:del_maestro AND ti:checkerboard"'])

    assert result.exit_code == 0


@pytest.mark.httpretty
def test_find_search_query_supports_parentheses(runner):
    body = pkg_resources.resource_string(
        __name__, os.path.join(
            'fixtures', (
                'search_query=au:del_maestro+ANDNOT+'
                '%28ti:checkerboard+OR+ti:Pyrochlore%29.xml')))
    httpretty.register_uri(httpretty.POST, API_BASE_URL, body=body)

    result = runner.invoke(cli, [
        'find', (
            'search_query=au:del_maestro ANDNOT '
            '(ti:checkerboard OR ti:Pyrochlore)')])

    assert result.exit_code == 0


@pytest.mark.httpretty
def test_find_search_query_supports_double_quotes(runner):
    body = pkg_resources.resource_string(
        __name__, os.path.join(
            'fixtures', (
                'search_query=au:del_maestro+AND+'
                'ti:"quantum+criticality".xml')))
    httpretty.register_uri(httpretty.POST, API_BASE_URL, body=body)

    result = runner.invoke(cli, [
        'find', 'au:del_maestro AND ti:"quantum criticality"'])

    assert result.exit_code == 0


@pytest.mark.httpretty
def test_find_supports_i_and_ids(runner):
    body = pkg_resources.resource_string(
        __name__, os.path.join(
            'fixtures', (
                'search_query=au:del_maestro+AND+'
                'ti:"quantum+criticality".xml')))
    httpretty.register_uri(httpretty.POST, API_BASE_URL, body=body)

    result = runner.invoke(cli, [
        'find', '-i', 'au:del_maestro AND ti:"quantum criticality"'])

    assert result.exit_code == 0
    assert result.output == '1111.2011v2 cond-mat/0607501v2'

    result = runner.invoke(cli, ['find', '--ids', 'au:del_maestro'])

    assert result.exit_code == 0
    assert result.output == '1111.2011v2 cond-mat/0607501v2'


@pytest.mark.httpretty
def test_find_supports_t_and_timeout(runner):
    body = pkg_resources.resource_string(
        __name__, os.path.join(
            'fixtures', (
                'search_query=au:del_maestro+AND+'
                'ti:"quantum+criticality".xml')))
    httpretty.register_uri(httpretty.POST, API_BASE_URL, body=body)

    result = runner.invoke(cli, [
        'find', '-t', '0', 'au:del_maestro AND ti:"quantum criticality"'])

    assert result.exit_code == 0

    result = runner.invoke(cli, [
        'find', '--timeout', '0', (
            'au:del_maestro AND ti:"quantum criticality"')])

    assert result.exit_code == 0
