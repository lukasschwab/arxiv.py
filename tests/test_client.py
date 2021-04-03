import unittest
from unittest.mock import patch, MagicMock
import arxiv
import feedparser
from urllib.parse import parse_qsl

# def get_parse_callable():

#     class Result(dict):

#         def get(self, k):
#             return 200

#     def parse(url):

#         for k, v in parse_qsl(url.split("?")[1]):
#             if k == "max_results":
#                 max_result = int(v)

#         result = Result()
#         result['entries'] = [
#             get_random_arxiv_entry() for _ in range(max_result)]
#         return result

#     return parse


class TestClient(unittest.TestCase):

#     def test_get_next(self):

#         search = Search(max_results=200, max_chunk_results=30, time_sleep=0)

#         with patch.object(feedparser, "parse", new_callable=get_parse_callable):

#             lenghts = [len(result) for result in search._get_next()]

#         self.assertListEqual(lenghts, [30, 30, 30, 30, 30, 30, 20])

#     def test_download(self):
#         search = Search(max_results=221, max_chunk_results=33, time_sleep=0)

#         with patch.object(feedparser, "parse", new_callable=get_parse_callable):
#             results = search.download(iterative=False)
#         self.assertEqual(len(results), 221)

#     def test_download_iterator(self):
#         search = Search(max_results=221, max_chunk_results=33, time_sleep=0)

#         with patch.object(feedparser, "parse", new_callable=get_parse_callable):
#             results = search.download(iterative=True)

#         self.assertTrue(callable(results))

#     def test_invalid_id(self):
#         self.assertEqual(len(query(id_list=["0000.0000"])),  0)

#     def test_query(self):

#         with patch.object(feedparser, "parse", new_callable=get_parse_callable):
#             result = query(
#                 query="sth",
#                 max_results=341)

#         self.assertEqual(len(result), 341)
    # @patch('feedparser.parse')
    # def test_num_retries(self, patch):
    #     # feedparser.parse = MagicMock(wraps=feedparser.parse)
    #     patch.wraps(feedparser.parse)
    #     # Should not retry if the feed is truly empty 
    #     list(arxiv.Search(query="asdflkjalsdkflkasdlfasd").get())
    #     self.assertEqual(patch.call_count, 1)

    def test_invalid_id(self):
        results = list(arxiv.Search(id_list=["0000.0000"]).get())
        self.assertEqual(len(results),  0)

    def test_max_results(self):
        client = arxiv.Client(page_size=10, delay_seconds=0)
        search = arxiv.Search(query="testing", max_results=2)
        results = [r for r in client.get(search)]
        self.assertEqual(len(results), 2)

    def test_query_page_count(self):
        client = arxiv.Client(page_size=10, delay_seconds=0)
        client._parse_feed = MagicMock(wraps=client._parse_feed)
        generator = client.get(arxiv.Search(query="testing", max_results=200))
        results = [r for r in generator]
        self.assertEqual(len(results), 200)
        self.assertEqual(client._parse_feed.call_count, 20)

    def test_no_duplicates(self):
        search = arxiv.Search("testing", max_results=100)
        ids = set()
        for r in search.get():
            self.assertFalse(r.entry_id in ids)
            ids.add(r.entry_id)