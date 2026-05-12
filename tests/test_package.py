"""
Tests for work-arounds to known arXiv API bugs.
"""

import unittest
from typing import Set


# ruff: noqa: F401
class TestPackage(unittest.TestCase):
    def get_public_classes(module: object) -> Set[str]:
        """
        Bodge: filter for the portion of the namespace that looks like exports.
        """
        return {name for name in dir(module) if name[0].isupper()}

    def test_deprecated_import_pattern(self):
        import arxiv as nondeprecated

        expected = TestPackage.get_public_classes(nondeprecated)
        self.assertTrue(expected, "should export non-empty set of classes; check the helper")

        from arxiv import arxiv as deprecated_from

        self.assertSetEqual(expected, TestPackage.get_public_classes(deprecated_from))

        import arxiv.arxiv as deprecated_dot

        self.assertSetEqual(expected, TestPackage.get_public_classes(deprecated_dot))


class TestUserAgent(unittest.TestCase):
    def test_user_agent_includes_version(self):
        from importlib.metadata import PackageNotFoundError, version

        from arxiv import _USER_AGENT

        try:
            expected = f"arxiv.py/{version('arxiv')}"
        except PackageNotFoundError:
            expected = "arxiv.py"
        self.assertEqual(_USER_AGENT, expected)
        self.assertTrue(_USER_AGENT.startswith("arxiv.py"))
