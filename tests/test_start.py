import unittest
from arxiv import query


class TestAPI(unittest.TestCase):

    def test_start_max_results_interaction(self):
        mr = 10
        results = query(query="quantum", start=100, max_results=mr)
        self.assertEqual(len(results), mr)

    def test_index_correct(self):
        no_start_results = query(query="quantum", max_results=100)
        start_results = query(query="quantum", max_results=1, start=99)
        self.assertEqual(no_start_results[-1]['id'], start_results[0]['id'])

    def test_default(self):
        no_start_results = query(query="quantum", max_results=10)
        start_results = query(query="quantum", start=0, max_results=10)
        self.assertEqual(no_start_results[0]['id'], start_results[0]['id'])
