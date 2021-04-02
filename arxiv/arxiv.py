# TODO: rename this file to arxiv.py
# TODO: do I want to deprecate pruning/processing and prefer just the raw entries?
# TODO: docstrings.
# TODO: retries
# TODO: generate and host documentation using pdoc: https://pdoc.dev/docs/pdoc.html#invoking-pdoc

import logging, time, feedparser

from urllib.parse import urlencode
from urllib.request import urlretrieve
from enum import Enum

logger = logging.getLogger(__name__)

class Client(object):
    query_url_format = 'http://export.arxiv.org/api/query?{}'
    """The arXiv query API endpoint format."""
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
    ] # TODO: reevaluate pruning.

    prune: bool
    """Whether to remove unhelpful fields from search results."""
    page_size: int
    """Maximum number of results fetched in a single API request."""
    time_sleep: int
    """Number of seconds to wait between API requests."""
    num_retries: int
    """Number of times to retry a failing API request."""

    # TODO: implement client
    def __init__(self, prune=True, page_size=1000, time_sleep=3, num_retries=3):
        """
        Construct an arXiv API client.
        """
        self.prune = prune
        self.page_size = page_size
        self.time_sleep = time_sleep
        self.num_retries = num_retries
        return

    def query(self, search):
        """
        query returns a generator of entries matching search using self's
        client configuration.
        """
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
        """
        Construct a request API for search that returns up to `page_size`
        results starting with the result at index `start`.
        """
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

class SortCriterion(Enum):
    """
    A SortCriterion identifies a property by which search results can be
    sorted. See [the arXiv API User's Manual: sort order for return
    results](https://arxiv.org/help/api/user-manual#sort).
    """
    Relevance = "relevance"
    LastUpdatedDate = "lastUpdatedDate"
    SubmittedDate = "submittedDate"

class SortOrder(Enum):
    """
    A SortOrder indicates order in which search results are sorted according
    to the specified arxiv.SortCriterion. See [the arXiv API User's Manual: sort
    order for return results](https://arxiv.org/help/api/user-manual#sort).
    """
    Ascending = "ascending"
    Descending = "descending"

class Search(object):
    """
    A specification for a search of arXiv's database. To run a search, use
    arxiv.query or arxiv.Client.query.
    """

    query: str
    """A string query. See [the arXiv API User's Manual: Details of Query
    Construction](https://arxiv.org/help/api/user-manual#query_details)."""
    id_list: list
    """
    A list of arXiv article IDs to which to limit the search. See [the arXiv
    API User's Manual](https://arxiv.org/help/api/user-manual#search_query_and_id_list)
    for documentation of the interaction between `query` and `id_list`.
    """
    max_results: float
    """
    The maximum number of results to be returned in an execution of this
    search. To fetch every result available, set `max_results=float('inf')`.
    """
    sort_by: SortCriterion
    """The sort criterion for results."""
    sort_order: SortOrder
    """The sort order for results."""

    def __init__(self, query="", id_list=[], max_results=float('inf'), sort_by=SortCriterion.Relevance, sort_order=SortOrder.Descending):
        self.query = query
        self.id_list = id_list
        self.max_results = max_results
        self.sort_by = sort_by
        self.sort_order = sort_order
    
    def url_args(self):
        """
        Returns a dict of search parameters that should be included in an API
        request for this search.
        """
        return {
            "search_query": self.query,
            "id_list": ','.join(self.id_list),
            "sortBy": self.sort_by.value,
            "sortOrder": self.sort_order.value
        }

def query(search):
    """
    Returns a generator of entries matching search using a default arxiv.Client.
    """
    return Client().query(search)

def to_filename(entry, extension=".pdf"):
    entry_id = entry.get('pdf_url').split('/')[-1]
    # Remove special characters from object title
    title = '_'.join(re.findall(r'\w+', obj.get('title', 'UNTITLED')))
    return "{}.{}{}".format(entry_id, title, extension)

def download(entry, dirpath='./', to_filename=to_filename, prefer_source_tarfile=False):
    """
    Download the .pdf corresponding to the result `entry`. If
    `prefer_source_tarfile`, download the .tar.gz source archive instead.
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