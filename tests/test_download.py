from __future__ import print_function
import arxiv
import tempfile
import unittest


class TestDownload(unittest.TestCase):

    def test_custom_slugify(self):

        # Returns the object id.
        def custom_slugify(obj):
            return obj.get('pdf_url').split('/')[-1]

        paper1 = arxiv.query(id_list=["1707.08567"])[0]
        paper2 = {"pdf_url": "http://arxiv.org/pdf/1707.08567v1",
                  "title": "The Paper Title"}

        with tempfile.TemporaryDirectory() as temp_dir:
            for paper in [paper1, paper2]:
                # Default behavior
                print(arxiv.download(paper))
                # Specify subdirectory
                print(arxiv.download(paper, dirpath=temp_dir))
                print(arxiv.download(paper, dirpath=temp_dir))
                # Specify slugify without subdir
                print(arxiv.download(paper, slugify=custom_slugify))
                # Specify slugify with subdir
                print(arxiv.download(paper, slugify=custom_slugify, dirpath=temp_dir))
                print(arxiv.download(paper, slugify=custom_slugify, dirpath=temp_dir))
