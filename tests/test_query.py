import unittest
import time
from arxiv import query


class TestAPI(unittest.TestCase):

    def setUp(self):
        # Wait a few seconds before
        time.sleep(3)

    def test_download_single_result(self):

        papers = query(id_list=["1707.08567"])

        self.assertEqual(type(papers), list)
        self.assertEqual(len(papers), 1)

        paper = papers[0]

        self.assertIn('author', paper)
        self.assertIn('author_detail', paper)
        self.assertIn('authors', paper)
        self.assertIn('affiliation', paper)
        self.assertIn('arxiv_comment', paper)
        self.assertIn('arxiv_primary_category', paper)
        self.assertIn('arxiv_url', paper)
        self.assertIn('doi', paper)
        self.assertIn('guidislink', paper)
        self.assertIn('id', paper)
        self.assertIn('journal_reference', paper)
        self.assertIn('links', paper)
        self.assertIn('published', paper)
        self.assertIn('published_parsed', paper)
        self.assertIn('pdf_url', paper)
        self.assertIn('updated', paper)
        self.assertIn('updated_parsed', paper)
        self.assertIn('summary_detail', paper)
        self.assertIn('summary', paper)
        self.assertIn('tags', paper)
        self.assertIn('title', paper)
        self.assertIn('title_detail', paper)

    def test_download_multiple_result(self):
        papers = query(id_list=["1707.08567", "1707.08567"])

        self.assertEqual(len(papers), 2)