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
        results = list(arxiv.Client().results(arxiv.Search(id_list=[paper_id])))
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].get_short_id(), paper_id)
        self.assertEqual(results[0].title, "0")
