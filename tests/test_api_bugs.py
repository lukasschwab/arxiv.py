"""
Regression tests for previously-known arXiv API bugs.
"""

import unittest

import arxiv


class TestAPIBugs(unittest.TestCase):
    def test_missing_title(self):
        """
        Regression test for the paper literally titled "0" (arxiv:2104.12255v1).

        The arXiv API used to omit the <title> element entirely for this paper,
        which required a client-side fallback. The API now returns
        ``<title>0</title>`` properly, so the workaround has been removed; this
        test ensures the title parses normally and we don't regress.

        + GitHub issue: https://github.com/lukasschwab/arxiv.py/issues/71
        + Bug report: https://groups.google.com/u/1/g/arxiv-api/c/ORENISrc5gc
        """
        paper_id = "2104.12255v1"
        results = list(arxiv.Search(id_list=[paper_id]).results())
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].get_short_id(), paper_id)
        self.assertEqual(results[0].title, "0")

    def test_long_id_list_does_not_414(self):
        """
        Regression test for issue #15: a long `id_list` used to produce an
        HTTP 414 (URI Too Long) when the parameters were encoded into the
        request URL. The client now sends parameters as form data over POST,
        which the arXiv API also accepts (see the API user manual).

        We don't care about the response contents here — only that the
        client formats the request such that the server doesn't reject it on
        size grounds. The test passes 700 fake-but-well-formed IDs, which
        balloons the GET-form URL well past 10KB.

        + GitHub issue: https://github.com/lukasschwab/arxiv.py/issues/15
        + API manual: https://info.arxiv.org/help/api/user-manual.html#31-calling-the-api
        """
        from unittest.mock import patch

        import requests

        ids = [f"1234.{i:05d}v1" for i in range(700)]
        captured: dict = {}

        def fake_post(self, url, **kwargs):  # type: ignore[no-untyped-def]
            captured["url"] = url
            captured["data"] = kwargs.get("data")
            resp = requests.Response()
            resp.status_code = 200
            resp._content = (
                b'<?xml version="1.0" encoding="UTF-8"?>'
                b'<feed xmlns="http://www.w3.org/2005/Atom" '
                b'xmlns:opensearch="http://a9.com/-/spec/opensearch/1.1/">'
                b"<opensearch:totalResults>0</opensearch:totalResults>"
                b"</feed>"
            )
            return resp

        with patch.object(requests.Session, "post", fake_post):
            list(arxiv.Client().results(arxiv.Search(id_list=ids)))

        # The endpoint URL itself stays short — IDs live in the POST body.
        self.assertEqual(captured["url"], arxiv.Client.query_url)
        self.assertNotIn("?", captured["url"])
        # And the body actually contains all the IDs we asked for.
        self.assertIn(ids[0], captured["data"]["id_list"])
        self.assertIn(ids[-1], captured["data"]["id_list"])
