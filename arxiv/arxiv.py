# TODO: errors and error handling, at least for the network calls.
#   Look into the API behavior; we probably still get 200s, but with feed
#   entries indicating errors.

import logging, time, feedparser, re, os

from datetime import datetime
from urllib.parse import urlencode
from urllib.request import urlretrieve

from enum import Enum
from typing import Generator, Dict, List

logger = logging.getLogger(__name__)


class Result(object):
    """An entry in an arXiv query results feed."""
    entry_id: str
    updated: datetime
    published: datetime
    title: str
    authors: list
    summary: str
    comment: str
    primary_category: str
    categories: List[str]
    links: list
    def __init__(
        self,
        entry_id: str,
        updated: datetime = datetime.min,
        published: datetime = datetime.min,
        title: str = "",
        authors: List['Result.Author'] = [],
        summary: str = "",
        comment: str = "",
        primary_category: str = "",
        categories: List[str] = [],
        links: List['Result.Link'] = []
    ):
        """
        Constructs an arXiv search result item. In most cases, prefer
        `_from_feed_entry` for parsing raw search results rather than parsing
        feed items yourself.
        """
        self.entry_id = entry_id
        self.updated = updated
        self.published = published
        self.title = title
        self.authors = authors
        self.summary = summary
        self.comment = comment
        self.primary_category = primary_category
        self.categories = categories
        self.links = links

    def _from_feed_entry(entry: feedparser.FeedParserDict) -> 'Result':
        """
        Converts a feedparser entry for an arXiv search result feed into a
        Result object.
        """
        return Result(
            entry_id=entry.id,
            updated=entry.updated_parsed,
            published=entry.published_parsed,
            title=re.sub(r'\s+', ' ', entry.title),
            authors=[Result.Author(a) for a in entry.authors],
            summary=entry.summary,
            comment=entry.get('comment'),
            primary_category=entry.arxiv_primary_category.get('term'),
            categories=[tag.get('term') for tag in entry.tags],
            links=[Result.Link(link) for link in entry.links]
        )
    
    def get_short_id(self) -> str:
        """
        Returns the short ID for this result. If the result URL is
        `"http://arxiv.org/abs/quant-ph/0201082v1"`, `result.get_short_id()`
        returns `"0201082v1"`.
        """
        return self.entry_id.split('/')[-1]
    
    def get_pdf_url(self) -> str:
        """
        Returns the URL of a PDF version of this result.
        """
        pdf_links = [l.href for l in self.links if l.title == 'pdf']
        if len(pdf_links) == 0:
            raise ValueError("Result does not have a PDF link")
        elif len(pdf_links) > 1:
            logger.warn(
                "%s has multiple PDF links; using %s",
                self.get_short_id(),
                pdf_links[0].href
            )
        return pdf_links[0]

    def _get_default_filename(self, extension: str = "pdf") -> str:
        """
        A default `to_filename` function for the extension given.
        """
        nonempty_title = self.title if self.title else "UNTITLED"
        # Remove disallowed characters.
        clean_title = '_'.join(re.findall(r'\w+', nonempty_title))
        return "{}.{}.{}".format(self.get_short_id(), clean_title, extension)

    def download_pdf(self, dirpath: str = './', filename: str = '') -> str:
        """
        Downloads the PDF for this result to the specified directory. The
        filename is generated by calling `to_filename(self)`.
        """
        if not filename:
            filename = self._get_default_filename()
        path = os.path.join(dirpath, filename)
        written_path, _ = urlretrieve(self.get_pdf_url(), path)
        return written_path

    def download_source(self, dirpath: str = './', filename: str = '') -> str:
        """
        Downloads the source tarfile for this result to the specified
        directory. The filename is generated by calling `to_filename(self)`.
        """
        if not filename:
            filename = self._get_default_filename('tar.gz')
        path = os.path.join(dirpath, filename)
        # Bodge: construct the source URL from the PDF URL.
        source_url = self.get_pdf_url().replace('/pdf/', '/src/')
        written_path, _ = urlretrieve(source_url, path)
        return written_path
    
    class Author(object):
        """
        A light inner class for representing a result's authors.
        """
        name: str
        def __init__(self, entry_author: feedparser.FeedParserDict):
            self.name = entry_author.name

    class Link(object):
        """
        A light inner class for representing a result's links.
        """
        href: str
        title: str
        rel: str
        content_type: str
        def __init__(self, feed_link: feedparser.FeedParserDict):
            self.href = feed_link.href
            self.title = feed_link.get('title')
            self.rel = feed_link.get('rel')
            self.content_type = feed_link.get('content_type')


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
    `Search.run` to use a default client or `Client.run` with a specific client.
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

    def __init__(
        self,
        query:str="",
        id_list:List[str]=[],
        max_results:float=float('inf'),
        sort_by:SortCriterion=SortCriterion.Relevance,
        sort_order:SortOrder=SortOrder.Descending
    ):
        """
        Construct an arXiv API search.
        """
        self.query = query
        self.id_list = id_list
        self.max_results = max_results
        self.sort_by = sort_by
        self.sort_order = sort_order
    
    def _url_args(self) -> Dict[str, str]:
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
    
    def get(self) -> Generator[Result, None, None]:
        """
        Executes the specified search using a default arXiv API client. For
        info on those defauts see `Client`; see also `Client.get`.
        """
        return Client().get(self)


class Client(object):
    query_url_format = 'http://export.arxiv.org/api/query?{}'
    """The arXiv query API endpoint format."""
    page_size: int
    """Maximum number of results fetched in a single API request."""
    delay_seconds: int
    """Number of seconds to wait between API requests."""
    num_retries: int
    """Number of times to retry a failing API request."""

    def __init__(
        self,
        page_size:int=100,
        delay_seconds:int=3,
        num_retries:int=3
    ):
        """
        Construct an arXiv API client.
        """
        self.page_size = page_size
        self.delay_seconds = delay_seconds
        self.num_retries = num_retries

    def get(self, search: Search) -> Generator[Result, None, None]:
        """
        Uses this client configuration to fetch one page of the search at a
        time, yielding the search results one by one, until `max_results`
        results have been yielded or there are no more search results.

        For more on using generators, see [Generators](https://wiki.python.org/moin/Generators).
        """
        offset = 0
        # Placeholder; this may be reduced according to the feed's
        # opensearch:totalResults value.
        total_results = search.max_results
        first_page = True
        while offset < total_results:
            if not first_page:
                time.sleep(self.delay_seconds)
            # Request next page of results.
            page_size = min(self.page_size, search.max_results-offset)
            page_url = self._format_url(search, offset, page_size)
            feed = self._parse_feed(page_url, first_page)
            if first_page:
                # NOTE: this is an ugly fix for a known bug. The totalresults
                # value is set to 1 for results with zero entries. If that API
                # bug is fixed, we can remove this conditional and always set
                # `total_results = min(...)`.
                if len(feed.entries) == 0:
                    total_results = 0
                else:
                    total_results = min(
                        total_results,
                        int(feed.feed.opensearch_totalresults)
                    )
                # Subsequent pages are not the first page.
                first_page = False
            # Update offset for next request: account for received results.
            offset += len(feed.entries)
            # Yield query results until page is exhausted.
            for entry in feed.entries:
                yield Result._from_feed_entry(entry)

    def _format_url(self, search: Search, start: int, page_size: int) -> str:
        """
        Construct a request API for search that returns up to `page_size`
        results starting with the result at index `start`.
        """
        url_args = search._url_args()
        url_args.update({
            "start": start,
            "max_results": page_size,
        })
        return self.query_url_format.format(urlencode(url_args))
    
    def _parse_feed(self, url: str, first_page: bool = True) -> feedparser.FeedParserDict:
        """
        Fetches the specified URL and parses it with feedparser. If a request
        fails or is unexpectedly empty, `_parse_feed` retries the request up to
        `self.num_retries` times.
        """
        for t in range(self.num_retries):
            logger.info("Requesting feed", extra={'try': t, 'url': url})
            feed = feedparser.parse(url)
            if feed.status != 200:
                logger.error(
                    "Requesting feed: HTTP error",
                    extra={'status': feed.status, 'try': t, 'url': url}
                )
            elif len(feed.entries) == 0 and not first_page:
                logger.info(
                    "Requesting feed: expected entries",
                    extra={'try': t, 'url': url}
                )
            else:
                return feed
        # TODO: raise an exception. This page really can't be fetched.
        raise Exception("Could not parse feed at URL")
