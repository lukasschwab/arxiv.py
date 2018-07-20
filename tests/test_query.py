import unittest
from arxiv import query


class TestAPI(unittest.TestCase):

    def test_download_on_id(self):
        papers = query(id_list=["1707.08567", "1707.08567"])

        self.assertEqual(type(papers), list)
        self.assertEqual(len(papers), 2)

        for paper in papers:

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
