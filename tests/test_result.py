import arxiv
import unittest
import re
import time
from datetime import datetime, timezone


class TestAPI(unittest.TestCase):

    def assert_nonempty(self, s):
        self.assertIsNotNone(s)
        self.assertNotEqual(s, '')

    def assert_valid_author(self, a: arxiv.Result.Author):
        self.assert_nonempty(a.name)

    def assert_valid_link(self, link: arxiv.Result.Link):
        self.assert_nonempty(link.href)

    def assert_valid_result(self, result: arxiv.Result):
        self.assert_nonempty(result.entry_id)
        self.assertIsNotNone(result.updated)
        self.assertIsNotNone(result.published)
        self.assert_nonempty(result.title)
        self.assertNotEqual(len(result.authors), 0)
        for author in result.authors:
            self.assert_valid_author(author)
        self.assert_nonempty(result.summary)
        self.assert_nonempty(result.primary_category)
        self.assertNotEqual(len(result.categories), 0)
        for category in result.categories:
            self.assert_nonempty(category)
        for link in result.links:
            self.assert_valid_link(link)
        self.assert_nonempty(result.pdf_url)

    def test_result_shape(self):
        max_results = 100
        search = arxiv.Search("testing", max_results=max_results)
        results = [r for r in search.get()]
        self.assertEqual(len(results), max_results)
        for result in results:
            self.assert_valid_result(result)

    def test_from_feed_entry(self):
        feed = arxiv.Client()._parse_feed(
            "http://export.arxiv.org/api/query?search_query=testing"
        )
        feed_entry = feed.entries[0]
        result = arxiv.Result._from_feed_entry(feed_entry)
        self.assert_valid_result(result)

    def test_get_short_id(self):
        result_id = "1707.08567"
        result = next(arxiv.Search(id_list=[result_id]).get())
        got = result.get_short_id()
        self.assertTrue(got.startswith(result_id))
        # Should be of form `1707.08567v1`.
        self.assertTrue(re.match(r'^{}v\d+$'.format(result_id), got))

    def test_to_datetime(self):
        """Test time.struct_time to datetime conversion."""
        # paper_published and paper_published_parsed correspond to
        # r._raw.published and r._raw.published_parsed for 1605.08386v1. It's
        # critical to the test that they remain equivalent.
        paper_published = '2016-05-26T17:59:46Z'
        paper_published_parsed = time.struct_time((2016, 5, 26, 17, 59, 46, 3, 147, 0))
        expected = datetime(2016, 5, 26, hour=17, minute=59, second=46, tzinfo=timezone.utc)
        actual = arxiv.Result._to_datetime(paper_published_parsed)
        self.assertEqual(actual, expected)
        self.assertEqual(actual.strftime("%Y-%m-%dT%H:%M:%SZ"), paper_published)
