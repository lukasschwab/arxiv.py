import arxiv
import unittest
import re
import time
from datetime import datetime, timezone


class TestResult(unittest.TestCase):
    def assert_nonempty(self, s):
        self.assertIsNotNone(s)
        self.assertNotEqual(s, "")

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
        client = arxiv.Client()
        max_results = 100
        search = arxiv.Search("testing", max_results=max_results)
        results = [r for r in client.results(search)]
        self.assertEqual(len(results), max_results)
        for result in results:
            self.assert_valid_result(result)

    def test_parse_feed(self):
        """`_parse_feed` should return a `ParsedFeed` of fully-built `Result`s."""
        client = arxiv.Client()
        # Use a fixed id_list so the fixture key is stable and the feed
        # contains exactly one well-known entry.
        form_data = client._format_form_data(
            arxiv.Search(id_list=["1605.08386"]), 0, client.page_size
        )
        feed = client._parse_feed(form_data)
        self.assertEqual(len(feed.results), 1)
        self.assert_valid_result(feed.results[0])

    def test_get_short_id(self):
        client = arxiv.Client()
        result_id = "1707.08567"
        result = next(client.results(arxiv.Search(id_list=[result_id])))
        got = result.get_short_id()
        self.assertTrue(got.startswith(result_id))
        # Should be of form `1707.08567v1`.
        self.assertTrue(re.match(r"^{}v\d+$".format(result_id), got))

    def test_to_datetime(self):
        """Test time.struct_time to datetime conversion."""
        # paper_published and paper_published_parsed correspond to
        # r._raw.published and r._raw.published_parsed for 1605.08386v1. It's
        # critical to the test that they remain equivalent.
        paper_published = "2016-05-26T17:59:46Z"
        paper_published_parsed = time.struct_time((2016, 5, 26, 17, 59, 46, 3, 147, 0))
        expected = datetime(2016, 5, 26, hour=17, minute=59, second=46, tzinfo=timezone.utc)
        actual = arxiv.Result._to_datetime(paper_published_parsed)
        self.assertEqual(actual, expected)
        self.assertEqual(actual.strftime("%Y-%m-%dT%H:%M:%SZ"), paper_published)

    def test_eq(self):
        # Results
        id = "some-result"
        result = arxiv.Result(entry_id=id)
        self.assertTrue(result == result)
        self.assertTrue(result == arxiv.Result(entry_id=id))
        self.assertTrue(arxiv.Result(entry_id=id) == result)
        self.assertFalse(result == arxiv.Result(entry_id="other"))
        self.assertFalse(result == id)
        # Authors
        name = "some-name"
        author = arxiv.Result.Author(name)
        self.assertTrue(author == author)
        self.assertTrue(author == arxiv.Result.Author(name))
        self.assertTrue(arxiv.Result.Author(name) == author)
        self.assertFalse(author == arxiv.Result.Author("other"))
        self.assertFalse(author == id)
        # Links
        href = "some-href"
        link = arxiv.Result.Link(href)
        self.assertTrue(link == link)
        self.assertTrue(link == arxiv.Result.Link(href))
        self.assertTrue(arxiv.Result.Link(href) == link)
        self.assertFalse(link == arxiv.Result.Link("other"))
        self.assertFalse(link == id)

    def test_legacy_ids(self):
        client = arxiv.Client()
        full_legacy_id = "quant-ph/0201082v1"
        result = next(client.results(arxiv.Search(id_list=[full_legacy_id])))
        self.assertEqual(result.get_short_id(), full_legacy_id)

    def test_author_affiliations(self):
        """Regression test for https://github.com/lukasschwab/arxiv.py/issues/62.

        The arXiv API exposes per-author affiliations via
        `<arxiv:affiliation>` children of `<author>` elements. This data was
        silently dropped by the previous feedparser-based implementation; it
        should now be available on `Result.Author.affiliation`.
        """
        # astro-ph/0601001 has four authors, each with a distinct affiliation.
        client = arxiv.Client()
        result = next(client.results(arxiv.Search(id_list=["astro-ph/0601001"])))
        self.assertEqual(len(result.authors), 4)
        names_and_affiliations = [(a.name, a.affiliation) for a in result.authors]
        self.assertEqual(
            names_and_affiliations,
            [
                ("Andrew Gould", ["Ohio State"]),
                ("Susan Dorsher", ["Ohio State"]),
                ("B. Scott Gaudi", ["CfA"]),
                ("Andrzej Udalski", ["Warsaw University Observatory"]),
            ],
        )

    def test_author_no_affiliation(self):
        """Most papers have no affiliation data; the field should be an empty list."""
        client = arxiv.Client()
        result = next(client.results(arxiv.Search(id_list=["1605.08386"])))
        for author in result.authors:
            self.assertEqual(author.affiliation, [])
