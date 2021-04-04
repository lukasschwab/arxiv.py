import unittest
from unittest.mock import MagicMock
import arxiv


class TestClient(unittest.TestCase):
    def test_invalid_id(self):
        results = list(arxiv.Search(id_list=["0000.0000"]).get())
        self.assertEqual(len(results), 0)

    def test_max_results(self):
        client = arxiv.Client(page_size=10, delay_seconds=0)
        search = arxiv.Search(query="testing", max_results=2)
        results = [r for r in client.get(search)]
        self.assertEqual(len(results), 2)

    def test_query_page_count(self):
        client = arxiv.Client(page_size=10, delay_seconds=0)
        client._parse_feed = MagicMock(wraps=client._parse_feed)
        generator = client.get(arxiv.Search(query="testing", max_results=55))
        results = [r for r in generator]
        self.assertEqual(len(results), 55)
        self.assertEqual(client._parse_feed.call_count, 6)

    def test_no_duplicates(self):
        search = arxiv.Search("testing", max_results=100)
        ids = set()
        for r in search.get():
            self.assertFalse(r.entry_id in ids)
            ids.add(r.entry_id)

    def test_retry(self):
        num_retries = 2
        broken_client = arxiv.Client(num_retries=num_retries)
        # Always returns a 500 status.
        broken_client.query_url_format = "https://httpstat.us/500?{}"

        def broken_get():
            search = arxiv.Search(query="quantum")
            return next(broken_client.get(search))

        self.assertRaises(arxiv.HTTPError, broken_get)
        for num_retries in [2, 5]:
            broken_client.num_retries = num_retries
            try:
                broken_get()
            except arxiv.HTTPError as e:
                self.assertEqual(e.retry, broken_client.num_retries - 1)
