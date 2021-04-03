# TODO: docstrings.
# TODO: generate and host documentation using pdoc: https://pdoc.dev/docs/pdoc.html#invoking-pdoc
#   Throw the docs-generating pdoc call into a pre-commit hook.
# TODO: errors and error handling, at least for the network calls.
#   Look into the API behavior; we probably still get 200s, but with feed
#   entries indicating errors.

import logging, time, feedparser

from urllib.parse import urlencode
from enum import Enum

from .result import Result

logger = logging.getLogger(__name__)

class Client(object):
    query_url_format = 'http://export.arxiv.org/api/query?{}'
    """The arXiv query API endpoint format."""

    prune: bool
    """Whether to remove unhelpful fields from search results."""
    page_size: int
    """Maximum number of results fetched in a single API request."""
    delay_seconds: int
    """Number of seconds to wait between API requests."""
    num_retries: int
    """Number of times to retry a failing API request."""

    def __init__(self, prune=True, page_size=100, delay_seconds=3, num_retries=3):
        """
        Construct an arXiv API client.
        """
        self.prune = prune
        self.page_size = page_size
        self.delay_seconds = delay_seconds
        self.num_retries = num_retries
        return

    def get(self, search):
        """
        Uses this client configuration to fetch one page of the search at a
        time, yielding the search results one by one, until `max_results`
        results have been yielded or there are no more search results.

        For more on using generators, see [Generators](https://wiki.python.org/moin/Generators).
        """
        offset = 0
        # Placeholder; this may be reduced according to the feed's opensearch:totalResults value.
        total_results = search.max_results
        first_page = True
        while offset < total_results:
            if not first_page:
                time.sleep(self.delay_seconds)
            page_size = min(self.page_size, search.max_results-offset)
            page_url = self._format_url(search, offset, page_size)
            feed = self._parse_feed(page_url)
            if first_page:
                total_results = min(total_results, int(feed.feed.opensearch_totalresults))
                first_page = False
            offset += len(feed.entries)
            for entry in feed.entries:
                yield Result._from_feed_entry(entry)

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
    to the specified arxiv.SortCriterion. See [the arXiv API User's Manual:
    sort order for return results](https://arxiv.org/help/api/user-manual#sort).
    """
    Ascending = "ascending"
    Descending = "descending"

class Search(object):
    """
    A specification for a search of arXiv's database. To run a search, use
    `query` or `Client.query`.
    """

    query: str
    """
    A string query. See [the arXiv API User's Manual: Details of Query
    Construction](https://arxiv.org/help/api/user-manual#query_details).
    """
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
    
    def get(self):
        """
        Executes the specified search using a default arXiv API client. For
        info on those defauts see `Client`; see also `Client.get`.
        """
        return Client().get(self)
