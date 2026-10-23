import unittest
from unittest.mock import MagicMock, call, patch
from urllib.parse import parse_qs, urlparse

import arxiv
from datetime import datetime, timedelta
from pytest import approx
from requests import Response


def empty_response(code: int) -> Response:
    r = Response()
    r.status_code = code
    r._content = b""
    return r


def atom_entry(short_id: str, valid: bool = True) -> str:
    published = "<published>2026-01-01T00:00:00Z</published>" if valid else ""
    return (
        "<entry>"
        f"<id>https://arxiv.org/abs/{short_id}</id>"
        "<updated>2026-01-01T00:00:00Z</updated>"
        f"{published}"
        "</entry>"
    )


def atom_feed(
    entries: list[tuple[str, bool]], total_results: int, start: int, page_size: int
) -> bytes:
    entry_xml = "".join(atom_entry(short_id, valid) for short_id, valid in entries)
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom"
      xmlns:opensearch="http://a9.com/-/spec/opensearch/1.1/">
  <opensearch:totalResults>{total_results}</opensearch:totalResults>
  <opensearch:itemsPerPage>{page_size}</opensearch:itemsPerPage>
  <opensearch:startIndex>{start}</opensearch:startIndex>
  {entry_xml}
</feed>
""".encode()


def paginated_client(
    entries: list[tuple[str, bool]], page_size: int = 2, empty_page_once: int | None = None
) -> tuple[arxiv.Client, list[int]]:
    starts: list[int] = []
    total_results = len(entries)

    def fake_get(url: str, **kwargs: object) -> Response:
        nonlocal empty_page_once
        del kwargs
        start = int(parse_qs(urlparse(url).query)["start"][0])
        starts.append(start)
        page = entries[start : start + page_size]
        if start == empty_page_once:
            page = []
            empty_page_once = None
        response = Response()
        response.status_code = 200
        response._content = atom_feed(page, total_results, start, page_size)
        return response

    client = arxiv.Client(page_size=page_size, delay_seconds=0, num_retries=0)
    client._session.get = fake_get
    return client, starts


class TestClient(unittest.TestCase):
    def test_invalid_format_id(self):
        with self.assertRaises(arxiv.HTTPError):
            list(arxiv.Client(num_retries=0).results(arxiv.Search(id_list=["abc"])))

    def test_invalid_id(self):
        results = list(arxiv.Client().results(arxiv.Search(id_list=["0000.0000"])))
        self.assertEqual(len(results), 0)

    def test_nonexistent_id_in_list(self):
        client = arxiv.Client()
        # Assert thrown error is handled and hidden by generator.
        results = list(client.results(arxiv.Search(id_list=["0808.05394"])))
        self.assertEqual(len(results), 0)
        # Generator should still yield valid entries.
        results = list(client.results(arxiv.Search(id_list=["0808.05394", "1707.08567"])))
        self.assertEqual(len(results), 1)

    def test_default_max_results(self):
        search = arxiv.Search(query="testing")
        self.assertEqual(search.max_results, 100)

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

    def test_pagination_uses_raw_entry_count(self):
        entries = [
            ("2601.00000", True),
            ("2601.00001", False),
            ("2601.00002", True),
            ("2601.00003", True),
            ("2601.00004", True),
        ]
        client, starts = paginated_client(entries)

        results = list(client.results(arxiv.Search(query="testing", max_results=5)))

        self.assertEqual(
            [result.get_short_id() for result in results],
            [
                "2601.00000",
                "2601.00002",
                "2601.00003",
                "2601.00004",
            ],
        )
        self.assertEqual(starts, [0, 2, 4])

    def test_all_invalid_first_page_does_not_stop_pagination(self):
        entries = [
            ("2601.00000", False),
            ("2601.00001", False),
            ("2601.00002", True),
        ]
        client, starts = paginated_client(entries)

        results = list(client.results(arxiv.Search(query="testing", max_results=3)))

        self.assertEqual([result.get_short_id() for result in results], ["2601.00002"])
        self.assertEqual(starts, [0, 2])

    def test_all_invalid_middle_page_does_not_raise(self):
        entries = [
            ("2601.00000", True),
            ("2601.00001", True),
            ("2601.00002", False),
            ("2601.00003", False),
            ("2601.00004", True),
        ]
        client, starts = paginated_client(entries)
        client.num_retries = 2

        results = list(client.results(arxiv.Search(query="testing", max_results=5)))

        self.assertEqual(
            [result.get_short_id() for result in results],
            ["2601.00000", "2601.00001", "2601.00004"],
        )
        self.assertEqual(starts, [0, 2, 4])

    def test_true_empty_middle_page_is_retried(self):
        entries = [(f"2601.0000{i}", True) for i in range(5)]
        client, starts = paginated_client(entries, empty_page_once=2)
        client.num_retries = 1

        results = list(client.results(arxiv.Search(query="testing", max_results=5)))

        self.assertEqual([result.get_short_id() for result in results], [e[0] for e in entries])
        self.assertEqual(starts, [0, 2, 2, 4])

    def test_manually_constructed_feed_without_raw_count(self):
        result = arxiv.Result(entry_id="https://arxiv.org/abs/2601.00000")
        feed = arxiv.ParsedFeed(arxiv._feed.FeedHeader(total_results=1), [result])
        client = arxiv.Client()

        with patch.object(client, "_parse_feed", return_value=feed):
            self.assertEqual(list(client.results(arxiv.Search(query="testing"))), [result])

    def test_all_invalid_final_page_does_not_raise(self):
        entries = [
            ("2601.00000", True),
            ("2601.00001", True),
            ("2601.00002", False),
            ("2601.00003", False),
        ]
        client, starts = paginated_client(entries)

        results = list(client.results(arxiv.Search(query="testing", max_results=4)))

        self.assertEqual(
            [result.get_short_id() for result in results], ["2601.00000", "2601.00001"]
        )
        self.assertEqual(starts, [0, 2])

    def test_pagination_respects_initial_offset_and_finite_limit(self):
        entries = [
            ("2601.00000", True),
            ("2601.00001", False),
            ("2601.00002", True),
            ("2601.00003", True),
            ("2601.00004", True),
        ]
        client, starts = paginated_client(entries)

        results = list(client.results(arxiv.Search(query="testing", max_results=3), offset=1))

        self.assertEqual(
            [result.get_short_id() for result in results], ["2601.00002", "2601.00003"]
        )
        self.assertEqual(starts, [1, 3])

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
                self.assertEqual(all_results[offset].entry_id, client_results[0].entry_id)

    def test_no_duplicates(self):
        search = arxiv.Search("testing", max_results=100)
        ids = set()
        for r in arxiv.Client().results(search):
            self.assertFalse(r.entry_id in ids)
            ids.add(r.entry_id)

    @patch("requests.Session.get", return_value=empty_response(500))
    @patch("time.sleep", return_value=None)
    def test_retry(self, mock_sleep, mock_get):
        broken_client = arxiv.Client()

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

    @patch("requests.Session.get", return_value=empty_response(200))
    @patch("time.sleep", return_value=None)
    def test_sleep_standard(self, mock_sleep, mock_get):
        client = arxiv.Client()
        url = client._format_url(arxiv.Search(query="quantum"), 0, 1)
        # A client should sleep until delay_seconds have passed.
        client._parse_feed(url)
        mock_sleep.assert_not_called()
        # Overwrite _last_request_dt to minimize flakiness: different
        # environments will have different page fetch times.
        client._last_request_dt = datetime.now()
        client._parse_feed(url)
        mock_sleep.assert_called_once_with(approx(client.delay_seconds, rel=1e-3))

    @patch("requests.Session.get", return_value=empty_response(200))
    @patch("time.sleep", return_value=None)
    def test_sleep_multiple_requests(self, mock_sleep, mock_get):
        client = arxiv.Client()
        url1 = client._format_url(arxiv.Search(query="quantum"), 0, 1)
        url2 = client._format_url(arxiv.Search(query="testing"), 0, 1)
        # Rate limiting is URL-independent; expect same behavior as in
        # `test_sleep_standard`.
        client._parse_feed(url1)
        mock_sleep.assert_not_called()
        client._last_request_dt = datetime.now()
        client._parse_feed(url2)
        mock_sleep.assert_called_once_with(approx(client.delay_seconds, rel=1e-3))

    @patch("requests.Session.get", return_value=empty_response(200))
    @patch("time.sleep", return_value=None)
    def test_sleep_elapsed(self, mock_sleep, mock_get):
        client = arxiv.Client()
        url = client._format_url(arxiv.Search(query="quantum"), 0, 1)
        # If _last_request_dt is less than delay_seconds ago, sleep.
        client._last_request_dt = datetime.now() - timedelta(seconds=client.delay_seconds - 1)
        client._parse_feed(url)
        mock_sleep.assert_called_once()
        mock_sleep.reset_mock()
        # If _last_request_dt is at least delay_seconds ago, don't sleep.
        client._last_request_dt = datetime.now() - timedelta(seconds=client.delay_seconds)
        client._parse_feed(url)
        mock_sleep.assert_not_called()

    @patch("requests.Session.get", return_value=empty_response(200))
    @patch("time.sleep", return_value=None)
    def test_sleep_zero_delay(self, mock_sleep, mock_get):
        client = arxiv.Client(delay_seconds=0)
        url = client._format_url(arxiv.Search(query="quantum"), 0, 1)
        client._parse_feed(url)
        client._parse_feed(url)
        mock_sleep.assert_not_called()

    @patch("requests.Session.get", return_value=empty_response(500))
    @patch("time.sleep", return_value=None)
    def test_sleep_between_errors(self, mock_sleep, mock_get):
        client = arxiv.Client()
        url = client._format_url(arxiv.Search(query="quantum"), 0, 1)
        try:
            client._parse_feed(url)
        except arxiv.HTTPError:
            pass
        # Should sleep between retries.
        mock_sleep.assert_called()
        self.assertEqual(mock_sleep.call_count, client.num_retries)
        mock_sleep.assert_has_calls(
            [
                call(approx(client.delay_seconds, abs=1e-2)),
            ]
            * client.num_retries
        )
