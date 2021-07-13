""".. include:: ../README.md"""
import logging
import time
import feedparser
import re
import os
import warnings

from urllib.parse import urlencode
from urllib.request import urlretrieve
from datetime import datetime, timedelta, timezone
from calendar import timegm

from enum import Enum
from typing import Dict, Generator, List

logger = logging.getLogger(__name__)

_DEFAULT_TIME = datetime.min


class Result(object):
    """
    An entry in an arXiv query results feed.

    See [the arXiv API User's Manual: Details of Atom Results
    Returned](https://arxiv.org/help/api/user-manual#_details_of_atom_results_returned).
    """

    entry_id: str
    """A url of the form `http://arxiv.org/abs/{id}`."""
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
    pdf_url: str
    """The URL of a PDF version of this result if present among links."""
    _raw: feedparser.FeedParserDict
    """
    The raw feedparser result object if this Result was constructed with
    Result._from_feed_entry.
    """

    def __init__(
        self,
        entry_id: str,
        updated: datetime = _DEFAULT_TIME,
        published: datetime = _DEFAULT_TIME,
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
        Constructs an arXiv search result item.

        In most cases, prefer using `Result._from_feed_entry` to parsing and
        constructing `Result`s yourself.
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
        # Calculated members
        self.pdf_url = Result._get_pdf_url(links)
        # Debugging
        self._raw = _raw

    def _from_feed_entry(entry: feedparser.FeedParserDict) -> 'Result':
        """
        Converts a feedparser entry for an arXiv search result feed into a
        Result object.
        """
        # Title attribute may be absent for certain titles. Defaulting to "0" as
        # it's the only title observed to cause this bug.
        # https://github.com/lukasschwab/arxiv.py/issues/71
        # title = entry.title if hasattr(entry, "title") else "0"
        title = "0"
        if hasattr(entry, "title"):
            title = entry.title
        else:
            logger.warning(
                "Result %s is missing title attribute; defaulting to '0'",
                entry.id
            )
        return Result(
            entry_id=entry.id,
            updated=Result._to_datetime(entry.updated_parsed),
            published=Result._to_datetime(entry.published_parsed),
            title=re.sub(r'\s+', ' ', title),
            authors=[Result.Author._from_feed_author(a) for a in entry.authors],
            summary=entry.summary,
            comment=entry.get('comment'),
            journal_ref=entry.get('arxiv_journal_ref'),
            doi=entry.get('arxiv_doi'),
            primary_category=entry.arxiv_primary_category.get('term'),
            categories=[tag.get('term') for tag in entry.tags],
            links=[Result.Link._from_feed_link(link) for link in entry.links],
            _raw=entry
        )

    def __str__(self) -> str:
        return self.entry_id

    def __repr__(self) -> str:
        return (
            '{}(entry_id={}, updated={}, published={}, title={}, authors={}, '
            'summary={}, comment={}, journal_ref={}, doi={}, '
            'primary_category={}, categories={}, links={})'
        ).format(
            _classname(self),
            repr(self.entry_id),
            repr(self.updated),
            repr(self.published),
            repr(self.title),
            repr(self.authors),
            repr(self.summary),
            repr(self.comment),
            repr(self.journal_ref),
            repr(self.doi),
            repr(self.primary_category),
            repr(self.categories),
            repr(self.links)
        )

    def __eq__(self, other) -> bool:
        if isinstance(other, Result):
            return self.entry_id == other.entry_id
        return False

    def get_short_id(self) -> str:
        """
        Returns the short ID for this result.

        + If the result URL is `"http://arxiv.org/abs/2107.05580v1"`,
        `result.get_short_id()` returns `2107.05580v1`.

        + If the result URL is `"http://arxiv.org/abs/quant-ph/0201082v1"`,
        `result.get_short_id()` returns `"quant-ph/0201082v1"` (the pre-March
        2007 arXiv identifier format).

        For an explanation of the difference between arXiv's legacy and current
        identifiers, see [Understanding the arXiv
        identifier](https://arxiv.org/help/arxiv_identifier).
        """
        return self.entry_id.split('arxiv.org/abs/')[-1]

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
        Downloads the PDF for this result to the specified directory.

        The filename is generated by calling `to_filename(self)`.
        """
        if not filename:
            filename = self._get_default_filename()
        path = os.path.join(dirpath, filename)
        written_path, _ = urlretrieve(self.pdf_url, path)
        return written_path

    def download_source(self, dirpath: str = './', filename: str = '') -> str:
        """
        Downloads the source tarfile for this result to the specified
        directory.

        The filename is generated by calling `to_filename(self)`.
        """
        if not filename:
            filename = self._get_default_filename('tar.gz')
        path = os.path.join(dirpath, filename)
        # Bodge: construct the source URL from the PDF URL.
        source_url = self.pdf_url.replace('/pdf/', '/src/')
        written_path, _ = urlretrieve(source_url, path)
        return written_path

    def _get_pdf_url(links: list) -> str:
        """
        Finds the PDF link among a result's links and returns its URL.

        Should only be called once for a given `Result`, in its constructor.
        After construction, the URL should be available in `Result.pdf_url`.
        """
        pdf_urls = [link.href for link in links if link.title == 'pdf']
        if len(pdf_urls) == 0:
            return None
        elif len(pdf_urls) > 1:
            logger.warning(
                "Result has multiple PDF links; using %s",
                pdf_urls[0]
            )
        return pdf_urls[0]

    def _to_datetime(ts: time.struct_time) -> datetime:
        """
        Converts a UTC time.struct_time into a time-zone-aware datetime.

        This will be replaced with feedparser functionality [when it becomes
        available](https://github.com/kurtmckee/feedparser/issues/212).
        """
        return datetime.fromtimestamp(timegm(ts), tz=timezone.utc)

    class Author(object):
        """
        A light inner class for representing a result's authors.
        """

        name: str
        """The author's name."""

        def __init__(self, name: str):
            """
            Constructs an `Author` with the specified name.

            In most cases, prefer using `Author._from_feed_author` to parsing
            and constructing `Author`s yourself.
            """
            self.name = name

        def _from_feed_author(
            feed_author: feedparser.FeedParserDict
        ) -> 'Result.Author':
            """
            Constructs an `Author` with the name specified in an author object
            from a feed entry.

            See usage in `Result._from_feed_entry`.
            """
            return Result.Author(feed_author.name)

        def __str__(self) -> str:
            return self.name

        def __repr__(self) -> str:
            return '{}({})'.format(_classname(self), repr(self.name))

        def __eq__(self, other) -> bool:
            if isinstance(other, Result.Author):
                return self.name == other.name
            return False

    class Link(object):
        """
        A light inner class for representing a result's links.
        """

        href: str
        """The link's `href` attribute."""
        title: str
        """The link's title."""
        rel: str
        """The link's relationship to the `Result`."""
        content_type: str
        """The link's HTTP content type."""

        def __init__(
            self,
            href: str,
            title: str = None,
            rel: str = None,
            content_type: str = None
        ):
            """
            Constructs a `Link` with the specified link metadata.

            In most cases, prefer using `Link._from_feed_link` to parsing and
            constructing `Link`s yourself.
            """
            self.href = href
            self.title = title
            self.rel = rel
            self.content_type = content_type

        def _from_feed_link(
            feed_link: feedparser.FeedParserDict
        ) -> 'Result.Link':
            """
            Constructs a `Link` with link metadata specified in a link object
            from a feed entry.

            See usage in `Result._from_feed_entry`.
            """
            return Result.Link(
                href=feed_link.href,
                title=feed_link.get('title'),
                rel=feed_link.get('rel'),
                content_type=feed_link.get('content_type')
            )

        def __str__(self) -> str:
            return self.href

        def __repr__(self) -> str:
            return '{}({}, title={}, rel={}, content_type={})'.format(
                _classname(self),
                repr(self.href),
                repr(self.title),
                repr(self.rel),
                repr(self.content_type)
            )

        def __eq__(self, other) -> bool:
            if isinstance(other, Result.Link):
                return self.href == other.href
            return False


class SortCriterion(Enum):
    """
    A SortCriterion identifies a property by which search results can be
    sorted.

    See [the arXiv API User's Manual: sort order for return
    results](https://arxiv.org/help/api/user-manual#sort).
    """
    Relevance = "relevance"
    LastUpdatedDate = "lastUpdatedDate"
    SubmittedDate = "submittedDate"


class SortOrder(Enum):
    """
    A SortOrder indicates order in which search results are sorted according
    to the specified arxiv.SortCriterion.

    See [the arXiv API User's Manual: sort order for return
    results](https://arxiv.org/help/api/user-manual#sort).
    """
    Ascending = "ascending"
    Descending = "descending"


class Search(object):
    """
    A specification for a search of arXiv's database.

    To run a search, use `Search.run` to use a default client or `Client.run`
    with a specific client.
    """

    query: str
    """
    A query string.

    See [the arXiv API User's Manual: Details of Query
    Construction](https://arxiv.org/help/api/user-manual#query_details).
    """
    id_list: list
    """
    A list of arXiv article IDs to which to limit the search.

    See [the arXiv API User's
    Manual](https://arxiv.org/help/api/user-manual#search_query_and_id_list)
    for documentation of the interaction between `query` and `id_list`.
    """
    max_results: float
    """
    The maximum number of results to be returned in an execution of this
    search.

    To fetch every result available, set `max_results=float('inf')`.
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
        Constructs an arXiv API search with the specified criteria.
        """
        self.query = query
        self.id_list = id_list
        self.max_results = max_results
        self.sort_by = sort_by
        self.sort_order = sort_order

    def __str__(self) -> str:
        # TODO: develop a more informative string representation.
        return repr(self)

    def __repr__(self) -> str:
        return (
            '{}(query={}, id_list={}, max_results={}, sort_by={}, '
            'sort_order={})'
        ).format(
            _classname(self),
            repr(self.query),
            repr(self.id_list),
            repr(self.max_results),
            repr(self.sort_by),
            repr(self.sort_order)
        )

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
        **Deprecated** after 1.2.0; use `Search.results`.
        """
        warnings.warn(
            "The 'get' method is deprecated, use 'results' instead",
            DeprecationWarning,
            stacklevel=2
        )
        return self.results()

    def results(self) -> Generator[Result, None, None]:
        """
        Executes the specified search using a default arXiv API client.

        For info on default behavior, see `Client.__init__` and `Client.results`.
        """
        return Client().results(self)


class Client(object):
    """
    Specifies a strategy for fetching results from arXiv's API.

    This class obscures pagination and retry logic, and exposes
    `Client.results`.
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
        Constructs an arXiv API client with the specified options.

        Note: the default parameters should provide a robust request strategy
        for most use cases. Extreme page sizes, delays, or retries risk
        violating the arXiv [API Terms of Use](https://arxiv.org/help/api/tou),
        brittle behavior, and inconsistent results.
        """
        self.page_size = page_size
        self.delay_seconds = delay_seconds
        self.num_retries = num_retries
        self._last_request_dt = None

    def __str__(self) -> str:
        # TODO: develop a more informative string representation.
        return repr(self)

    def __repr__(self) -> str:
        return '{}(page_size={}, delay_seconds={}, num_retries={})'.format(
            _classname(self),
            repr(self.page_size),
            repr(self.delay_seconds),
            repr(self.num_retries)
        )

    def get(self, search: Search) -> Generator[Result, None, None]:
        """
        **Deprecated** after 1.2.0; use `Client.results`.
        """
        warnings.warn(
            "The 'get' method is deprecated, use 'results' instead",
            DeprecationWarning,
            stacklevel=2
        )
        return self.results(search)

    def results(self, search: Search) -> Generator[Result, None, None]:
        """
        Uses this client configuration to fetch one page of the search results
        at a time, yielding the parsed `Result`s, until `max_results` results
        have been yielded or there are no more search results.

        If all tries fail, raises an `UnexpectedEmptyPageError` or `HTTPError`.

        For more on using generators, see
        [Generators](https://wiki.python.org/moin/Generators).
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
        Fetches the specified URL and parses it with feedparser.

        If a request fails or is unexpectedly empty, retries the request up to
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
                err = HTTPError(url, retry, feed)
            elif len(feed.entries) == 0 and not first_page:
                err = UnexpectedEmptyPageError(url, retry)
            else:
                return feed
        # Feed was never returned in self.num_retries tries. Raise the last
        # exception encountered.
        raise err


class ArxivError(Exception):
    """This package's base Exception class."""

    url: str
    """The feed URL that could not be fetched."""
    message: str
    """Message describing what caused this error."""

    def __init__(self, url: str, message: str):
        """
        Constructs an `ArxivError` encountered while fetching the specified URL.
        """
        self.url = url
        self.message = message
        # logger.info(self.message, extra=extra)
        super().__init__(self.message)

    def __str__(self) -> str:
        return '{} ({})'.format(self.message, self.url)


class UnexpectedEmptyPageError(ArxivError):
    """
    An error raised when a page of results that should be non-empty is empty.

    This should never happen in theory, but happens sporadically due to
    brittleness in the underlying arXiv API; usually resolved by retries.

    See `Client.results` for usage.
    """

    retry: int
    """The request retry number which encountered this error, zero-indexed."""

    def __init__(self, url: str, retry: int):
        """
        Constructs an `UnexpectedEmptyPageError` encountered for the specified
        API URL after `retry` tries.
        """
        self.url = url
        self.retry = retry
        super().__init__(url, "Page of results was unexpectedly empty")

    def __repr__(self) -> str:
        return '{}({}, {})'.format(
            _classname(self),
            repr(self.url),
            repr(self.retry)
        )


class HTTPError(ArxivError):
    """
    A non-200 status encountered while fetching a page of results.

    See `Client.results` for usage.
    """

    retry: int
    """The request retry number which encountered this error, zero-indexed."""
    status: int
    """The HTTP status reported by feedparser."""
    entry: feedparser.FeedParserDict
    """The feed entry describing the error, if present."""

    def __init__(self, url: str, retry: int, feed: feedparser.FeedParserDict):
        """
        Constructs an `HTTPError` for the specified status code, encountered for
        the specified API URL after `retry` tries.
        """
        self.retry = retry
        self.url = url
        self.status = feed.status
        # If the feed is valid and includes a single entry, trust it's an
        # explanation.
        if not feed.bozo and len(feed.entries) == 1:
            self.entry = feed.entries[0]
        else:
            self.entry = None
        super().__init__(
            url,
            "Page request resulted in HTTP {}: {}".format(
                self.status,
                self.entry.summary if self.entry else None,
            ),
        )

    def __repr__(self) -> str:
        return '{}({}, {}, {})'.format(
            _classname(self),
            repr(self.url),
            repr(self.retry),
            repr(self.status)
        )


def _classname(o):
    """A helper function for use in __repr__ methods: arxiv.Result.Link."""
    return 'arxiv.{}'.format(o.__class__.__qualname__)
