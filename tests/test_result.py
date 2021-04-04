import arxiv
import unittest
import re


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
