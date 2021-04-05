import unittest
from unittest.mock import MagicMock, patch
import arxiv
from datetime import datetime, timedelta
from pytest import approx


class TestClient(unittest.TestCase):
    def test_invalid_id(self):
        results = list(arxiv.Search(id_list=["0000.0000"]).results())
        self.assertEqual(len(results), 0)

    def test_max_results(self):
        client = arxiv.Client(page_size=10, delay_seconds=0)
        search = arxiv.Search(query="testing", max_results=2)
        results = [r for r in client.results(search)]
        self.assertEqual(len(results), 2)

    def test_query_page_count(self):
        client = arxiv.Client(page_size=10, delay_seconds=0)
        client._parse_feed = MagicMock(wraps=client._parse_feed)
        generator = client.results(arxiv.Search(query="testing", max_results=55))
        results = [r for r in generator]
        self.assertEqual(len(results), 55)
        self.assertEqual(client._parse_feed.call_count, 6)

    def test_no_duplicates(self):
        search = arxiv.Search("testing", max_results=100)
        ids = set()
        for r in search.results():
            self.assertFalse(r.entry_id in ids)
            ids.add(r.entry_id)

    def test_retry(self):
        # broken_client always encounters a 500 status.
        broken_client = arxiv.Client(page_size=1, delay_seconds=0)
        broken_client.query_url_format = "https://httpstat.us/500?{}"

        def broken_get():
            search = arxiv.Search(query="quantum")
            return next(broken_client.results(search))

        self.assertRaises(arxiv.HTTPError, broken_get)
        for num_retries in [2, 5]:
            broken_client.num_retries = num_retries
            try:
                broken_get()
            except arxiv.HTTPError as e:
                self.assertEqual(e.retry, broken_client.num_retries)

    @patch('time.sleep', return_value=None)
    def test_sleep_standard(self, patched_time_sleep):
        client = arxiv.Client(page_size=1)
        url = client._format_url(arxiv.Search(query="quantum"), 0, 1)
        # A client should sleep until delay_seconds have passed.
        client._parse_feed(url)
        patched_time_sleep.assert_not_called()
        # Overwrite _last_request_dt to minimize flakiness: different
        # environments will have different page fetch times.
        client._last_request_dt = datetime.now()
        client._parse_feed(url)
        patched_time_sleep.assert_called_once_with(
            approx(client.delay_seconds, rel=1e-3)
        )

    @patch('time.sleep', return_value=None)
    def test_sleep_multiple_requests(self, patched_time_sleep):
        client = arxiv.Client(page_size=1)
        url1 = client._format_url(arxiv.Search(query="quantum"), 0, 1)
        url2 = client._format_url(arxiv.Search(query="testing"), 0, 1)
        # Rate limiting is URL-independent; expect same behavior as in
        # `test_sleep_standard`.
        client._parse_feed(url1)
        patched_time_sleep.assert_not_called()
        client._last_request_dt = datetime.now()
        client._parse_feed(url2)
        patched_time_sleep.assert_called_once_with(
            approx(client.delay_seconds, rel=1e-3)
        )

    @patch('time.sleep', return_value=None)
    def test_sleep_elapsed(self, patched_time_sleep):
        client = arxiv.Client(page_size=1)
        url = client._format_url(arxiv.Search(query="quantum"), 0, 1)
        # If _last_request_dt is less than delay_seconds ago, sleep.
        client._last_request_dt = (
            datetime.now() - timedelta(seconds=client.delay_seconds-1)
        )
        client._parse_feed(url)
        patched_time_sleep.assert_called_once()
        patched_time_sleep.reset_mock()
        # If _last_request_dt is at least delay_seconds ago, don't sleep.
        client._last_request_dt = (
            datetime.now() - timedelta(seconds=client.delay_seconds)
        )
        client._parse_feed(url)
        patched_time_sleep.assert_not_called()

    @patch('time.sleep', return_value=None)
    def test_sleep_zero_delay(self, patched_time_sleep):
        client = arxiv.Client(page_size=1, delay_seconds=0)
        url = client._format_url(arxiv.Search(query="quantum"), 0, 1)
        client._parse_feed(url)
        client._parse_feed(url)
        patched_time_sleep.assert_not_called()
