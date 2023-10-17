import unittest
from unittest.mock import MagicMock, call, patch
import arxiv
from datetime import datetime, timedelta
from pytest import approx


class TestClient(unittest.TestCase):
    def test_invalid_format_id(self):
        with self.assertRaises(arxiv.HTTPError):
            list(arxiv.Client(num_retries=0).results(arxiv.Search(id_list=["abc"])))

    def test_invalid_id(self):
        results = list(arxiv.Search(id_list=["0000.0000"]).results())
        self.assertEqual(len(results), 0)

    def test_nonexistent_id_in_list(self):
        client = arxiv.Client()
        # Assert thrown error is handled and hidden by generator.
        results = list(client.results(arxiv.Search(id_list=["0808.05394"])))
        self.assertEqual(len(results), 0)
        # Generator should still yield valid entries.
        results = list(
            client.results(arxiv.Search(id_list=["0808.05394", "1707.08567"]))
        )
        self.assertEqual(len(results), 1)

    def test_max_results(self):
        client = arxiv.Client(page_size=10)
        search = arxiv.Search(query="testing", max_results=2)
        results = [r for r in client.results(search)]
        self.assertEqual(len(results), 2)

    def test_query_page_count(self):
        client = arxiv.Client(page_size=10)
        client._parse_feed = MagicMock(wraps=client._parse_feed)
        generator = client.results(arxiv.Search(query="testing", max_results=55))
        results = [r for r in generator]

        # NOTE: don't directly assert on call count; allow for retries.
        unique_urls = set()
        for parse_call in client._parse_feed.call_args_list:
            args, _kwargs = parse_call
            unique_urls.add(args[0])

        self.assertEqual(len(results), 55)
        self.assertSetEqual(
            unique_urls,
            {
                "https://export.arxiv.org/api/query?search_query=testing&id_list=&sortBy=relevance&sortOrder=descending&start=0&max_results=10",
                "https://export.arxiv.org/api/query?search_query=testing&id_list=&sortBy=relevance&sortOrder=descending&start=10&max_results=10",
                "https://export.arxiv.org/api/query?search_query=testing&id_list=&sortBy=relevance&sortOrder=descending&start=20&max_results=10",
                "https://export.arxiv.org/api/query?search_query=testing&id_list=&sortBy=relevance&sortOrder=descending&start=30&max_results=10",
                "https://export.arxiv.org/api/query?search_query=testing&id_list=&sortBy=relevance&sortOrder=descending&start=40&max_results=10",
                "https://export.arxiv.org/api/query?search_query=testing&id_list=&sortBy=relevance&sortOrder=descending&start=50&max_results=10",
            },
        )

    def test_offset(self):
        max_results = 10
        search = arxiv.Search(query="testing", max_results=max_results)
        client = arxiv.Client(page_size=10)

        default = list(client.results(search))
        no_offset = list(client.results(search))
        self.assertListEqual(default, no_offset)

        offset = max_results // 2
        half_offset = list(client.results(search, offset=offset))
        self.assertListEqual(default[offset:], half_offset)

        offset_above_max_results = list(client.results(search, offset=max_results))
        self.assertListEqual(offset_above_max_results, [])

    def test_search_results_offset(self):
        # NOTE: page size is irrelevant here.
        client = arxiv.Client(page_size=15)
        search = arxiv.Search(query="testing", max_results=10)
        all_results = list(client.results(search, offset=0))
        self.assertEqual(len(all_results), 10)

        for offset in [0, 5, 9, 10, 11]:
            client_results = list(client.results(search, offset=offset))
            self.assertEqual(len(client_results), max(0, search.max_results - offset))
            if client_results:
                self.assertEqual(
                    all_results[offset].entry_id, client_results[0].entry_id
                )

    def test_no_duplicates(self):
        search = arxiv.Search("testing", max_results=100)
        ids = set()
        for r in search.results():
            self.assertFalse(r.entry_id in ids)
            ids.add(r.entry_id)

    @patch("time.sleep", return_value=None)
    def test_retry(self, patched_time_sleep):
        broken_client = TestClient.get_code_client(500)

        def broken_get():
            search = arxiv.Search(query="quantum")
            return next(broken_client.results(search))

        self.assertRaises(arxiv.HTTPError, broken_get)

        for num_retries in [2, 5]:
            broken_client.num_retries = num_retries
            try:
                broken_get()
                self.fail("broken_get didn't throw HTTPError")
            except arxiv.HTTPError as e:
                self.assertEqual(e.status, 500)
                self.assertEqual(e.retry, broken_client.num_retries)

    @patch("time.sleep", return_value=None)
    def test_sleep_standard(self, patched_time_sleep):
        client = TestClient.get_code_client(200)
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

    @patch("time.sleep", return_value=None)
    def test_sleep_multiple_requests(self, patched_time_sleep):
        client = TestClient.get_code_client(200)
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

    @patch("time.sleep", return_value=None)
    def test_sleep_elapsed(self, patched_time_sleep):
        client = TestClient.get_code_client(200)
        url = client._format_url(arxiv.Search(query="quantum"), 0, 1)
        # If _last_request_dt is less than delay_seconds ago, sleep.
        client._last_request_dt = datetime.now() - timedelta(
            seconds=client.delay_seconds - 1
        )
        client._parse_feed(url)
        patched_time_sleep.assert_called_once()
        patched_time_sleep.reset_mock()
        # If _last_request_dt is at least delay_seconds ago, don't sleep.
        client._last_request_dt = datetime.now() - timedelta(
            seconds=client.delay_seconds
        )
        client._parse_feed(url)
        patched_time_sleep.assert_not_called()

    @patch("time.sleep", return_value=None)
    def test_sleep_zero_delay(self, patched_time_sleep):
        client = TestClient.get_code_client(200, delay_seconds=0)
        client.query_url_format = "https://httpstat.us/200?{}"
        url = client._format_url(arxiv.Search(query="quantum"), 0, 1)
        client._parse_feed(url)
        client._parse_feed(url)
        patched_time_sleep.assert_not_called()

    @patch("time.sleep", return_value=None)
    def test_sleep_between_errors(self, patched_time_sleep):
        client = TestClient.get_code_client(500)
        url = client._format_url(arxiv.Search(query="quantum"), 0, 1)
        try:
            client._parse_feed(url)
        except arxiv.HTTPError:
            pass
        # Should sleep between retries.
        patched_time_sleep.assert_called()
        self.assertEqual(patched_time_sleep.call_count, client.num_retries)
        patched_time_sleep.assert_has_calls(
            [
                call(approx(client.delay_seconds, abs=1e-2)),
            ]
            * client.num_retries
        )

    def get_code_client(code: int, delay_seconds=0.1, num_retries=3) -> arxiv.Client:
        """
        get_code_client returns an arxiv.Cient with HTTP requests routed to
        httpstat.us.
        """
        client = arxiv.Client(delay_seconds=delay_seconds, num_retries=num_retries)
        client.query_url_format = "https://httpstat.us/{}?".format(code) + "{}"
        return client
