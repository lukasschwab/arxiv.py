import unittest
try:
    from unittest.mock import patch
except ImportError:
    from mock import patch
from arxiv import Search
from arxiv import query
import numpy as np
import feedparser

try:
    # Python 2
    from urlparse import parse_qsl
except ImportError:
    # Python 3
    from urllib.parse import parse_qsl

arxiv_keys = [
    'author',
    'author_detail',
    'id',
    'arxiv_affiliation',
    'arxiv_comment',
    'arxiv_primary_category',
    'link',
    'arxiv_doi',
    'guidislink',
    'arxiv_journal_reference',
    'links',
    'published',
    'published_parsed',
    'pdf_url',
    'updated',
    'updated_parse',
    'summary_detail',
    'summary',
    'tags',
    'title',
    'title_detail']


def get_random_str():
    return "".join(np.random.choice(['A', 'B', 'C'], 10))


def get_random_arxiv_entry():

    entry = dict()

    for key in arxiv_keys:
        entry[key] = get_random_str()

    entry['authors'] = [
            {'name': get_random_str()},
            {'name': get_random_str()},
            {'name': get_random_str()},
        ]

    return entry


def get_parse_callable():

    class Result(dict):

        def get(self, k):
            return 200

    def parse(url):

        for k, v in parse_qsl(url.split("?")[1]):
            if k == "max_results":
                max_result = int(v)

        result = Result()
        result['entries'] = [
            get_random_arxiv_entry() for _ in range(max_result)]
        return result

    return parse


class TestSearch(unittest.TestCase):

    def test_get_next(self):

        search = Search(max_results=200, max_chunk_results=30, time_sleep=0)

        with patch.object(feedparser, "parse", new_callable=get_parse_callable):

            lenghts = [len(result) for result in search._get_next()]

        self.assertListEqual(lenghts, [30, 30, 30, 30, 30, 30, 20])

    def test_download(self):
        search = Search(max_results=221, max_chunk_results=33, time_sleep=0)

        with patch.object(feedparser, "parse", new_callable=get_parse_callable):
            results = search.download(iterative=False)
        self.assertEqual(len(results), 221)

    def test_download_iterator(self):
        search = Search(max_results=221, max_chunk_results=33, time_sleep=0)

        with patch.object(feedparser, "parse", new_callable=get_parse_callable):
            results = search.download(iterative=True)

        self.assertTrue(callable(results))

    def test_invalid_id(self):
        self.assertEqual(len(query(id_list=["0000.0000"])),  0)

    def test_query(self):

        with patch.object(feedparser, "parse", new_callable=get_parse_callable):
            result = query(
                query="sth",
                max_results=341)

        self.assertEqual(len(result), 341)

    def test_query_iterator(self):

        iterator = query(
            query="sth",
            max_results=200,
            max_chunk_results=111,
            iterative=True)

        with patch.object(feedparser, "parse", new_callable=get_parse_callable):
            results = [r for r in iterator()]

        self.assertEqual(len(results), 200)
