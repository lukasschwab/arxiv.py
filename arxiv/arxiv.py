import logging
import time
import feedparser
import re
import os

from urllib.parse import urlencode
from urllib.request import urlretrieve
from datetime import datetime, timedelta

from enum import Enum
from typing import Dict, Generator, List

logger = logging.getLogger(__name__)

_DEFAULT_TIME = time.struct_time((0, 0, 0, 0, 0, 0, 0, 0, 0, 0))


class Result(object):
    """
    An entry in an arXiv query results feed.
    See [the arXiv API User's Manual: Details of Atom Results
    Returned](https://arxiv.org/help/api/user-manual#_details_of_atom_results_returned).
    """

    entry_id: str
    """A url `http://arxiv.org/abs/{id}`."""
    updated: time.struct_time
    """When the result was last updated."""
    published: time.struct_time
    """When the result was originally published."""
    title: str
    """The title of the result."""
    authors: list
    """The result's authors."""
    summary: str
    """The result abstrace."""
    comment: str
    """The authors' comment if present."""
    journal_ref: str
    """A journal reference if present."""
    doi: str
    """A URL for the resolved DOI to an external resource if present."""
    primary_category: str
    """
    The result's primary arXiv category. See [arXiv: Category
    Taxonomy](https://arxiv.org/category_taxonomy).
    """
    categories: List[str]
    """
    All of the result's categories. See [arXiv: Category
    Taxonomy](https://arxiv.org/category_taxonomy).
    """
    links: list
    """Up to three URLs associated with this result."""
    _raw: feedparser.FeedParserDict
    """
    The raw feedparser result object if this Result was constructed with
    Result._from_feed_entry.
    """

    def __init__(
        self,
        entry_id: str,
        updated: time.struct_time = _DEFAULT_TIME,
        published: time.struct_time = _DEFAULT_TIME,
        title: str = "",
        authors: List['Result.Author'] = [],
        summary: str = "",
        comment: str = "",
        journal_ref: str = "",
        doi: str = "",
        primary_category: str = "",
        categories: List[str] = [],
        links: List['Result.Link'] = [],
        _raw: feedparser.FeedParserDict = None,
    ):
        """
        Constructs an arXiv search result item. In most cases, prefer using
        `_from_feed_entry` to parsing and constructing feed items yourself.
        """
        self.entry_id = entry_id
        self.updated = updated
        self.published = published
        self.title = title
        self.authors = authors
        self.summary = summary
        self.comment = comment
        self.journal_ref = journal_ref
        self.doi = doi
        self.primary_category = primary_category
        self.categories = categories
        self.links = links
        self._raw = _raw

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
            journal_ref=entry.get('arxiv_journal_ref'),
            doi=entry.get('arxiv_doi'),
            primary_category=entry.arxiv_primary_category.get('term'),
            categories=[tag.get('term') for tag in entry.tags],
            links=[Result.Link(link) for link in entry.links],
            _raw=entry
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
        pdf_links = [link.href for link in self.links if link.title == 'pdf']
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
    `Search.run` to use a default client or `Client.run` with a specific
    client.
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
        query: str = "",
        id_list: List[str] = [],
        max_results: float = float('inf'),
        sort_by: SortCriterion = SortCriterion.Relevance,
        sort_order: SortOrder = SortOrder.Descending
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
        info on those defauts see `Client`; see also `(Client).get`.
        """
        return Client().get(self)


class Client(object):
    """
    Specifies a strategy for fetching results from arXiv's API; it obscures
    pagination and retry logic, and exposes `(Client).get`.
    """

    query_url_format = 'http://export.arxiv.org/api/query?{}'
    """The arXiv query API endpoint format."""
    page_size: int
    """Maximum number of results fetched in a single API request."""
    delay_seconds: int
    """Number of seconds to wait between API requests."""
    num_retries: int
    """Number of times to retry a failing API request."""
    _last_request_dt: datetime

    def __init__(
        self,
        page_size: int = 100,
        delay_seconds: int = 3,
        num_retries: int = 3
    ):
        """
        Construct an arXiv API client.
        """
        self.page_size = page_size
        self.delay_seconds = delay_seconds
        self.num_retries = num_retries
        self._last_request_dt = None

    def get(self, search: Search) -> Generator[Result, None, None]:
        """
        Uses this client configuration to fetch one page of the search at a
        time, yielding the search results one by one, until `max_results`
        results have been yielded or there are no more search results.

        If all tries fail, raises an `UnexpectedEmptyPageError` or `HTTPError`.

        For more on using generators, see [Generators](https://wiki.python.org/moin/Generators).
        """
        offset = 0
        # total_results may be reduced according to the feed's
        # opensearch:totalResults value.
        total_results = search.max_results
        first_page = True
        while offset < total_results:
            page_size = min(self.page_size, search.max_results - offset)
            logger.info("Requesting {} results at offset {}".format(
                page_size,
                offset,
            ))
            page_url = self._format_url(search, offset, page_size)
            feed = self._parse_feed(page_url, first_page)
            if first_page:
                # NOTE: this is an ugly fix for a known bug. The totalresults
                # value is set to 1 for results with zero entries. If that API
                # bug is fixed, we can remove this conditional and always set
                # `total_results = min(...)`.
                if len(feed.entries) == 0:
                    logger.info("Got empty results; stopping generation")
                    total_results = 0
                else:
                    total_results = min(
                        total_results,
                        int(feed.feed.opensearch_totalresults)
                    )
                    logger.info("Got first page; {} of {} results available".format(
                        total_results,
                        search.max_results
                    ))
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

    # NOTE: if erroneous outcomes are so common that it's necessary to sleep
    # after requests that return errors, _parse_feed can be rewritten
    # recursively.
    def _parse_feed(
        self,
        url: str,
        first_page: bool = True
    ) -> feedparser.FeedParserDict:
        """
        Fetches the specified URL and parses it with feedparser. If a request
        fails or is unexpectedly empty, `_parse_feed` retries the request up to
        `self.num_retries` times.

        Enforces `self.delay_seconds`: if that number of seconds has not passed
        since `_parse_feed` was last called, sleeps until delay_seconds seconds
        have passed.
        """
        # If this call would violate the rate limit, sleep until it doesn't.
        if self._last_request_dt is not None:
            required = timedelta(seconds=self.delay_seconds)
            since_last_request = datetime.now() - self._last_request_dt
            if since_last_request < required:
                to_sleep = (required - since_last_request).total_seconds()
                logger.info("Sleeping for %f seconds", to_sleep)
                time.sleep(to_sleep)
        # self.delay_seconds seconds have passed since last call. Fetch results.
        err = None
        for retry in range(self.num_retries):
            logger.info("Requesting page of results", extra={
                'url': url,
                'first_page': first_page,
                'retry': retry,
                'last_err': err.message if err is not None else None,
            })
            feed = feedparser.parse(url)
            self._last_request_dt = datetime.now()
            if feed.status != 200:
                err = HTTPError(url, retry, feed.status)
            elif len(feed.entries) == 0 and not first_page:
                err = UnexpectedEmptyPageError(url, retry)
            else:
                return feed
        # Feed was never returned in self.num_retries tries. Raise the last
        # exception encountered.
        raise err


class ArxivError(Exception):
    url: str
    """The feed URL that could not be fetched."""
    message: str
    """Message explaining what went wrong."""
    def __init__(self, url, message):
        self.url = url
        self.message = message
        # logger.info(self.message, extra=extra)
        super().__init__(self.message)


class UnexpectedEmptyPageError(ArxivError):
    """
    An error raised when a page of results that should be non-empty is empty.
    This should never happen in theory, but happens sporadically due to
    brittleness in the underlying arXiv API; usually resolved by retries.
    """
    retry: int
    """The request retry number which encountered this error, zero-indexed."""
    def __init__(self, url: str, retry: int):
        self.url = url
        self.retry = retry
        super().__init__(url, "Page of results was unexpectedly empty")


class HTTPError(ArxivError):
    """A non-200 status encountered while fetching a page of results."""
    retry: int
    """The request retry number which encountered this error, zero-indexed."""
    status: int
    """The HTTP status reported by feedparser."""
    def __init__(self, url: str, retry: int, status: int):
        self.retry = retry
        self.url = url
        self.status = status
        super().__init__(
            url,
            "Page request resulted in HTTP {}".format(self.status),
        )
