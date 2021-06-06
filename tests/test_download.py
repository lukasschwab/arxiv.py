from arxiv import arxiv
import os
import shutil
import tempfile
import unittest


class TestDownload(unittest.TestCase):

    @classmethod
    def setUpClass(self):
        self.fetched_result = next(arxiv.Search(id_list=["1605.08386"]).results())

    @classmethod
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    @classmethod
    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_download_from_query(self):
        self.fetched_result.download_pdf(dirpath=self.temp_dir)
        self.assertTrue(os.path.exists(os.path.join(
            self.temp_dir,
            '1605.08386v1.Heat_bath_random_walks_with_Markov_bases.pdf')
        ))

    def test_download_tarfile_from_query(self):
        self.fetched_result.download_source(dirpath=self.temp_dir)
        self.assertTrue(os.path.exists(os.path.join(
            self.temp_dir,
            '1605.08386v1.Heat_bath_random_walks_with_Markov_bases.tar.gz'
        )))

    def test_download_with_custom_slugify_from_query(self):
        fn = 'custom-filename.extension'
        self.fetched_result.download_pdf(dirpath=self.temp_dir, filename=fn)
        self.assertTrue(os.path.exists(os.path.join(self.temp_dir, fn)))
