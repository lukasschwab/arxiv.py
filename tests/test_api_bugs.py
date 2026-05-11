"""
Tests for work-arounds to known arXiv API bugs.
"""

import arxiv
import pytest
import unittest


class TestAPIBugs(unittest.TestCase):
    def test_missing_title(self):
        """
        Papers with the title "0" do not have a title element in the Atom feed.

        It's unclear whether other falsey titles (e.g. "False", "null", or empty
        titles) are allowed by arXiv and are impacted by this bug. This may also
        surface for other expected fields (e.g. author names).

        + GitHub issue: https://github.com/lukasschwab/arxiv.py/issues/71
        + Bug report: https://groups.google.com/u/1/g/arxiv-api/c/ORENISrc5gc
        """
        paper_without_title = "2104.12255v1"
        try:
            results = list(arxiv.Search(id_list=[paper_without_title]).results())
            self.assertEqual(len(results), 1)
            self.assertEqual(results[0].get_short_id(), paper_without_title)
        except AttributeError:
            self.fail("got AttributeError fetching paper without title")


# Regression tests that require the live API (no offline fixtures).
# These verify fixes in the arXiv API itself, not in the client.


@pytest.mark.live_only
class TestAPIRegressions(unittest.TestCase):
    def test_invalid_id_list_entry_does_not_duplicate_results(self):
        """
        Mixing invalid and valid IDs in id_list should not duplicate results.

        Previously, the arXiv API reported opensearch_totalresults inclusive of
        invalid IDs, which caused the client to over-paginate and return
        duplicate entries for valid papers.

        This was fixed on the API side: invalid IDs now contribute 0 to
        totalresults.

        + GitHub issue: https://github.com/lukasschwab/arxiv.py/issues/82
        """
        # Single invalid ID should yield no results.
        results = list(arxiv.Search(id_list=["0000.0000"]).results())
        self.assertEqual(len(results), 0)

        # Mixed invalid + valid IDs: only the valid paper should appear, once.
        results = list(
            arxiv.Search(id_list=["0000.0000", "1707.08567"]).results()
        )
        self.assertEqual(len(results), 1)
        self.assertIn("1707.08567", results[0].entry_id)
