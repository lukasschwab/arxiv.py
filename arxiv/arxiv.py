# TODO: rename this file to arxiv.py
# TODO: do I want to deprecate pruning/processing and prefer just the raw entries?
# TODO: docstrings.
# TODO: retries

import logging, time, feedparser

from urllib.parse import urlencode
from urllib.request import urlretrieve

logger = logging.getLogger(__name__)

class Client(object):
    query_url_format = 'http://export.arxiv.org/api/query?{}'
    prune_keys = [
        'updated_parsed',
        'published_parsed',
        'arxiv_primary_category',
        'summary_detail',
        'author',
        'author_detail',
        'links',
        'guidislink',
        'title_detail',
        'tags',
        'id'
    ]

    # TODO: implement client
    def __init__(self, prune=True, page_size=1000, time_sleep=3, num_retries=3):
        self.prune = prune
        self.page_size = page_size
        self.time_sleep = time_sleep
        self.num_retries = num_retries
        return

    def query(search):
        # TODO
        return []

    def _iterator(self, search):
        offset = 0
        # Placeholder; this may be reduced according to the feed's opensearch:totalResults value.
        total_results = search.max_results
        first_page = True
        while offset < total_results:
            if not first_page:
                time.sleep(self.time_sleep)
            page_size = min(self.page_size, search.max_results-offset)
            page_url = self._format_url(search, offset, page_size)
            feed = self._parse_feed(page_url)
            if first_page:
                total_results = min(total_results, int(feed.feed.opensearch_totalresults))
                first_page = False
            offset += len(feed.entries)
            for entry in feed.entries:
                yield self._process_entry(entry)

    def _format_url(self, search, start, page_size):
        url_args = search.url_args()
        url_args.update({
            "start": start,
            "max_results": page_size,
        })
        return self.query_url_format.format(urlencode(url_args))
    
    def _parse_feed(self, url):
        print("##### GETTING", url)
        for t in range(self.num_retries):
            feed = feedparser.parse(url)
            if feed.status == 200 and len(feed.entries) > 0:
                return feed
            logger.error("HTTP Error {} in query on try {}".format(feed.get('status', 'no status'), t))
            print("##### Retrying", url)
        # TODO: raise an exception. This page really can't be fetched.
        raise Exception("Could not parse feed at URL")
    
    def _process_entry(self, entry):
        # TODO: there's much more than just pruning in the last one.
        # Probably actually define a well-typed entry class.
        if self.prune:
            for key in Client.prune_keys:
                if key in entry:
                    del entry[key]
        return entry

class Search(object):
    def __init__(self, query="", id_list=[], max_results=float('inf'), sort_by="relevance", sort_order="descending"):
        self.query = query
        self.id_list = id_list
        self.max_results = max_results
        self.sort_by = sort_by
        self.sort_order = sort_order
    
    def url_args(self):
        return {
            "search_query": self.query,
            "id_list": ','.join(self.id_list),
            "sortBy": self.sort_by,
            "sortOrder": self.sort_order
        }
    
    def default():
        return Search()

def query(search):
    """
    query returns a generator of entries matching search using a default arxiv.Client.
    """
    return Client().query(search)

def to_filename(entry, extension=".pdf"):
    entry_id = entry.get('pdf_url').split('/')[-1]
    # Remove special characters from object title
    title = '_'.join(re.findall(r'\w+', obj.get('title', 'UNTITLED')))
    return "{}.{}{}".format(entry_id, title, extension)

def download(entry, dirpath='./', to_filename=to_filename, prefer_source_tarfile=False):
    """
    Download the .pdf corresponding to the result object 'obj'. If prefer_source_tarfile==True, download the source .tar.gz instead.
    """
    url = entry.get('pdf_url')
    if not url:
        print("Object has no PDF URL.")
        return
    if dirpath[-1] != '/':
        dirpath += '/'
    if prefer_source_tarfile:
        url = re.sub(r'/pdf/', "/src/", url)
        path = dirpath + to_filename(obj) + '.tar.gz'
    else:
        path = dirpath + to_filename(obj) + '.pdf'
    urlretrieve(url, path)
    return path