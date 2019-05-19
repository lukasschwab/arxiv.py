import arxiv
import os
import shutil
import tempfile
import unittest


# Returns the object id.
def custom_slugify(obj):
    return obj.get('pdf_url').split('/')[-1]


class TestDownload(unittest.TestCase):

    @classmethod
    def setUpClass(self):

        self.paper_query = arxiv.query(id_list=["1605.08386"])[0]
        self.paper_dict = {
            "pdf_url": "http://arxiv.org/pdf/1605.08386v1",
            "title": "The Paper Title"}

    @classmethod
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    @classmethod
    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_download_with_custom_slugify_from_query(self):
        arxiv.download(self.paper_query, slugify=custom_slugify, dirpath=self.temp_dir)
        self.assertTrue(
                os.path.exists(
                    os.path.join(self.temp_dir, '1605.08386v1.pdf')
                )
        )

    def test_download_with_custom_slugify_from_dict(self):
        arxiv.download(self.paper_dict, slugify=custom_slugify, dirpath=self.temp_dir)
        self.assertTrue(
                os.path.exists(
                    os.path.join(self.temp_dir, '1605.08386v1.pdf')
                )
        )

    def test_download_from_dict(self):
        arxiv.download(self.paper_dict, dirpath=self.temp_dir)
        self.assertTrue(
                os.path.exists(
                    os.path.join(
                        self.temp_dir,
                        '1605.08386v1.The_Paper_Title.pdf')
                )
        )

    def test_download_from_query(self):
        arxiv.download(self.paper_query, dirpath=self.temp_dir)
        self.assertTrue(
                os.path.exists(
                    os.path.join(
                        self.temp_dir,
                        '1605.08386v1.Heat_bath_random_walks_with_Markov_bases.pdf')
                )
        )
