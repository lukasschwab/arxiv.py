import pickle
import unittest

import arxiv


class TestErrorPickle(unittest.TestCase):
    """Regression tests for https://github.com/lukasschwab/arxiv.py/issues/191."""

    def test_arxiv_error_pickle_roundtrip(self):
        err = arxiv.ArxivError(url="http://example.com", retry=1, message="test")
        restored = pickle.loads(pickle.dumps(err))
        self.assertEqual(restored.url, err.url)
        self.assertEqual(restored.retry, err.retry)
        self.assertEqual(restored.message, err.message)
        self.assertEqual(str(restored), str(err))

    def test_http_error_pickle_roundtrip(self):
        err = arxiv.HTTPError(url="http://export.arxiv.org/api/query", retry=3, status=503)
        restored = pickle.loads(pickle.dumps(err))
        self.assertEqual(restored.url, err.url)
        self.assertEqual(restored.retry, err.retry)
        self.assertEqual(restored.status, err.status)
        self.assertIsInstance(restored.status, int)
        self.assertEqual(str(restored), str(err))
        self.assertEqual(repr(restored), repr(err))

    def test_unexpected_empty_page_error_pickle_roundtrip(self):
        err = arxiv.UnexpectedEmptyPageError(
            url="http://export.arxiv.org/api/query", retry=2, raw_feed="<xml/>"
        )
        restored = pickle.loads(pickle.dumps(err))
        self.assertEqual(restored.url, err.url)
        self.assertEqual(restored.retry, err.retry)
        self.assertEqual(restored.raw_feed, err.raw_feed)
        self.assertEqual(str(restored), str(err))
        self.assertEqual(repr(restored), repr(err))

    def test_http_error_double_roundtrip(self):
        """Ensure repeated pickle round-trips don't degrade the object."""
        err = arxiv.HTTPError(url="http://export.arxiv.org/api/query", retry=3, status=503)
        restored = pickle.loads(pickle.dumps(err))
        restored2 = pickle.loads(pickle.dumps(restored))
        self.assertEqual(restored2.status, 503)
        self.assertEqual(restored2.args, err.args)
        self.assertEqual(str(restored2), str(err))
