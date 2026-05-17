""".. include:: ../README.md"""

from __future__ import annotations

import logging
import time
import itertools
import requests

from importlib.metadata import PackageNotFoundError, version
from urllib.parse import urlencode
from datetime import datetime, timedelta, timezone
from calendar import timegm

from enum import Enum
from typing import Generator, Iterator

from . import _feed
from ._feed import ParsedFeed


logger = logging.getLogger(__name__)

try:
    __version__ = version("arxiv")
except PackageNotFoundError:
    __version__ = "0.0.0+unknown"

_USER_AGENT = f"arxiv.py/{__version__}"

_DEFAULT_TIME = datetime.min


class Result:
    """
    An entry in an arXiv query results feed.

    See [the arXiv API User's Manual: Details of Atom Results
    Returned](https://arxiv.org/help/api/user-manual#_details_of_atom_results_returned).
    """

    entry_id: str
    """A url of the form `https://arxiv.org/abs/{id}`."""
    updated: datetime
    """When the result was last updated."""
    published: datetime
    """When the result was originally published."""
    title: str
    """The title of the result."""
    authors: list[Result.Author]
    """The result's authors, including any `<arxiv:affiliation>` data."""
    summary: str
    """The result abstract."""
    comment: str | None
    """The authors' comment if present."""
    journal_ref: str | None
    """A journal reference if present."""
    doi: str | None
    """A URL for the resolved DOI to an external resource if present."""
    primary_category: str
    """
    The result's primary arXiv category. See [arXiv: Category
    Taxonomy](https://arxiv.org/category_taxonomy).
    """
    categories: list[str]
    """
    All of the result's categories. See [arXiv: Category
    Taxonomy](https://arxiv.org/category_taxonomy).
    """
    links: list[Result.Link]
    """Up to three URLs associated with this result."""
    pdf_url: str | None
    """The URL of a PDF version of this result if present among links."""

    def __init__(
        self,
        entry_id: str,
        updated: datetime = _DEFAULT_TIME,
        published: datetime = _DEFAULT_TIME,
        title: str = "",
        authors: list[Result.Author] | None = None,
        summary: str = "",
        comment: str = "",
        journal_ref: str = "",
        doi: str = "",
        primary_category: str = "",
        categories: list[str] | None = None,
        links: list[Result.Link] | None = None,
    ):
        """
        Constructs an arXiv search result item.

        In most cases, results are produced by `Client.results`, which parses
        API responses internally.
        """
        self.entry_id = entry_id
        self.updated = updated
        self.published = published
        self.title = title
        self.authors = authors or []
        self.summary = summary
        self.comment = comment
        self.journal_ref = journal_ref
        self.doi = doi
        self.primary_category = primary_category
        self.categories = categories or []
        self.links = links or []
        # Calculated members
        self.pdf_url = Result._get_pdf_url(self.links)

    def __str__(self) -> str:
        return self.entry_id

    def __repr__(self) -> str:
        return (
            "{}(entry_id={}, updated={}, published={}, title={}, authors={}, "
            "summary={}, comment={}, journal_ref={}, doi={}, "
            "primary_category={}, categories={}, links={})"
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
            repr(self.links),
        )

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Result):
            return self.entry_id == other.entry_id
        return False

    def get_short_id(self) -> str:
        """
        Returns the short ID for this result.

        + If the result URL is `"https://arxiv.org/abs/2107.05580v1"`,
        `result.get_short_id()` returns `2107.05580v1`.

        + If the result URL is `"https://arxiv.org/abs/quant-ph/0201082v1"`,
        `result.get_short_id()` returns `"quant-ph/0201082v1"` (the pre-March
        2007 arXiv identifier format).

        For an explanation of the difference between arXiv's legacy and current
        identifiers, see [Understanding the arXiv
        identifier](https://arxiv.org/help/arxiv_identifier).
        """
        return self.entry_id.split("arxiv.org/abs/")[-1]

    def source_url(self) -> str | None:
        """
        Derives a URL for the source tarfile for this result.
        """
        if self.pdf_url is None:
            return None
        return self.pdf_url.replace("/pdf/", "/src/")

    @staticmethod
    def _get_pdf_url(links: list[Result.Link]) -> str | None:
        """
        Finds the PDF link among a result's links and returns its URL.

        Should only be called once for a given `Result`, in its constructor.
        After construction, the URL should be available in `Result.pdf_url`.
        """
        pdf_urls = [link.href for link in links if link.title == "pdf"]
        if len(pdf_urls) == 0:
            return None
        elif len(pdf_urls) > 1:
            logger.warning("Result has multiple PDF links; using %s", pdf_urls[0])
        return pdf_urls[0]

    @staticmethod
    def _to_datetime(ts: time.struct_time) -> datetime:
        """
        Converts a UTC `time.struct_time` into a time-zone-aware `datetime`.

        Retained as a stable utility for callers that historically relied on
        feedparser's `*_parsed` time tuples; the internal Atom parser produces
        `datetime` objects directly.
        """
        return datetime.fromtimestamp(timegm(ts), tz=timezone.utc)

    class Author:
        """
        A light inner class for representing a result's authors.
        """

        name: str
        """The author's name."""
        affiliation: list[str]
        """
        Any `<arxiv:affiliation>` values associated with this author. Most
        results have no affiliation data and this is an empty list; some
        results have one or more affiliation strings per author.

        See https://github.com/lukasschwab/arxiv.py/issues/62.
        """

        def __init__(self, name: str, affiliation: list[str] | None = None):
            """
            Constructs an `Author` with the specified name and (optional)
            affiliations.
            """
            self.name = name
            self.affiliation = affiliation or []

        def __str__(self) -> str:
            return self.name

        def __repr__(self) -> str:
            if self.affiliation:
                return "{}({}, affiliation={})".format(
                    _classname(self), repr(self.name), repr(self.affiliation)
                )
            return "{}({})".format(_classname(self), repr(self.name))

        def __eq__(self, other: object) -> bool:
            if isinstance(other, Result.Author):
                return self.name == other.name
            return False

    class Link:
        """
        A light inner class for representing a result's links.
        """

        href: str
        """The link's `href` attribute."""
        title: str | None
        """The link's title."""
        rel: str
        """The link's relationship to the `Result`."""
        content_type: str | None
        """The link's HTTP content type."""

        def __init__(
            self,
            href: str,
            title: str | None = None,
            rel: str = "",
            content_type: str | None = None,
        ):
            """
            Constructs a `Link` with the specified link metadata.
            """
            self.href = href
            self.title = title
            self.rel = rel
            self.content_type = content_type

        def __str__(self) -> str:
            return self.href

        def __repr__(self) -> str:
            return "{}({}, title={}, rel={}, content_type={})".format(
                _classname(self),
                repr(self.href),
                repr(self.title),
                repr(self.rel),
                repr(self.content_type),
            )

        def __eq__(self, other: object) -> bool:
            if isinstance(other, Result.Link):
                return self.href == other.href
            return False

    class MissingFieldError(Exception):
        """
        An error indicating an entry is unparseable because it lacks required
        fields.
        """

        missing_field: str
        """The required field missing from the would-be entry."""
        message: str
        """Message describing what caused this error."""

        def __init__(self, missing_field: str):
            self.missing_field = missing_field
            self.message = "Entry from arXiv missing required info"

        def __repr__(self) -> str:
            return "{}({})".format(_classname(self), repr(self.missing_field))


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


class Search:
    """
    A specification for a search of arXiv's database.

    To run a search, use `Search.run` to use a default client or `Client.run`
    with a specific client.
    """

    query: str
    """
    A query string.

    This should be unencoded. Use `au:del_maestro AND ti:checkerboard`, not
    `au:del_maestro+AND+ti:checkerboard`.

    See [the arXiv API User's Manual: Details of Query
    Construction](https://arxiv.org/help/api/user-manual#query_details).
    """
    id_list: list[str]
    """
    A list of arXiv article IDs to which to limit the search.

    See [the arXiv API User's
    Manual](https://arxiv.org/help/api/user-manual#search_query_and_id_list)
    for documentation of the interaction between `query` and `id_list`.
    """
    max_results: int | None
    """
    The maximum number of results to be returned in an execution of this
    search. To fetch every result available, set `max_results=None`.

    The API's limit is 300,000 results per query.
    """
    sort_by: SortCriterion
    """The sort criterion for results."""
    sort_order: SortOrder
    """The sort order for results."""

    def __init__(
        self,
        query: str = "",
        id_list: list[str] | None = None,
        max_results: int | None = 100,
        sort_by: SortCriterion = SortCriterion.Relevance,
        sort_order: SortOrder = SortOrder.Descending,
    ):
        """
        Constructs an arXiv API search with the specified criteria.
        """
        self.query = query
        self.id_list = id_list or []
        self.max_results = max_results
        self.sort_by = sort_by
        self.sort_order = sort_order

    def __str__(self) -> str:
        if self.query and self.id_list:
            return f"Search(query='{self.query}', id_list={len(self.id_list)} items)"
        elif self.query:
            return f"Search(query='{self.query}')"
        elif self.id_list:
            return f"Search(id_list={len(self.id_list)} items)"
        else:
            return "Search(empty)"

    def __repr__(self) -> str:
        return ("{}(query={}, id_list={}, max_results={}, sort_by={}, sort_order={})").format(
            _classname(self),
            repr(self.query),
            repr(self.id_list),
            repr(self.max_results),
            repr(self.sort_by),
            repr(self.sort_order),
        )

    def _url_args(self) -> dict[str, str]:
        """
        Returns a dict of search parameters that should be included in an API
        request for this search.
        """
        return {
            "search_query": self.query,
            "id_list": ",".join(self.id_list),
            "sortBy": self.sort_by.value,
            "sortOrder": self.sort_order.value,
        }


class Client:
    """
    Specifies a strategy for fetching results from arXiv's API.

    This class obscures pagination and retry logic, and exposes
    `Client.results`.
    """

    query_url_format = "https://export.arxiv.org/api/query?{}"
    """
    The arXiv query API endpoint format.
    """
    page_size: int
    """
    Maximum number of results fetched in a single API request. Smaller pages can
    be retrieved faster, but may require more round-trips.

    The API's limit is 2000 results per page.
    """
    delay_seconds: float
    """
    Number of seconds to wait between API requests.

    [arXiv's Terms of Use](https://arxiv.org/help/api/tou) ask that you "make no
    more than one request every three seconds."
    """
    num_retries: int
    """
    Number of times to retry a failing API request before raising an Exception.
    """

    _last_request_dt: datetime | None
    _session: requests.Session

    def __init__(self, page_size: int = 100, delay_seconds: float = 3.0, num_retries: int = 3):
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
        self._session = requests.Session()

    def __str__(self) -> str:
        return f"Client(page_size={self.page_size}, delay={self.delay_seconds}s, retries={self.num_retries})"

    def __repr__(self) -> str:
        return "{}(page_size={}, delay_seconds={}, num_retries={})".format(
            _classname(self),
            repr(self.page_size),
            repr(self.delay_seconds),
            repr(self.num_retries),
        )

    def results(self, search: Search, offset: int = 0) -> Iterator[Result]:
        """
        Uses this client configuration to fetch one page of the search results
        at a time, yielding the parsed `Result`s, until `max_results` results
        have been yielded or there are no more search results.

        If all tries fail, raises an `UnexpectedEmptyPageError` or `HTTPError`.

        Setting a nonzero `offset` discards leading records in the result set.
        When `offset` is greater than or equal to `search.max_results`, the full
        result set is discarded.

        For more on using generators, see
        [Generators](https://wiki.python.org/moin/Generators).
        """
        limit = search.max_results - offset if search.max_results else None
        if limit and limit < 0:
            return iter(())
        return itertools.islice(self._results(search, offset), limit)

    def _results(self, search: Search, offset: int = 0) -> Generator[Result, None, None]:
        page_url = self._format_url(search, offset, self.page_size)
        feed = self._parse_feed(page_url, first_page=True)
        if not feed.results:
            logger.info("Got empty first page; stopping generation")
            return
        total_results = feed.header.total_results
        logger.info(
            "Got first page: %d of %d total results",
            len(feed.results),
            total_results,
        )

        while feed.results:
            yield from feed.results
            offset += len(feed.results)
            if offset >= total_results:
                break
            page_url = self._format_url(search, offset, self.page_size)
            feed = self._parse_feed(page_url, first_page=False)

    def _format_url(self, search: Search, start: int, page_size: int) -> str:
        """
        Construct a request API for search that returns up to `page_size`
        results starting with the result at index `start`.
        """
        url_args = search._url_args()
        url_args.update(
            {
                "start": str(start),
                "max_results": str(page_size),
            }
        )
        return self.query_url_format.format(urlencode(url_args))

    def _parse_feed(self, url: str, first_page: bool = True, _try_index: int = 0) -> ParsedFeed:
        """
        Fetches the specified URL and parses it as an Atom feed.

        If a request fails or is unexpectedly empty, retries the request up to
        `self.num_retries` times.
        """
        try:
            return self.__try_parse_feed(url, first_page=first_page, try_index=_try_index)
        except (
            HTTPError,
            UnexpectedEmptyPageError,
            requests.exceptions.ConnectionError,
        ) as err:
            if _try_index < self.num_retries:
                logger.debug("Got error (try %d): %s", _try_index, err)
                return self._parse_feed(url, first_page=first_page, _try_index=_try_index + 1)
            logger.debug("Giving up (try %d): %s", _try_index, err)
            raise err

    def __try_parse_feed(
        self,
        url: str,
        first_page: bool,
        try_index: int,
    ) -> ParsedFeed:
        """
        Recursive helper for _parse_feed. Enforces `self.delay_seconds`: if that
        number of seconds has not passed since `_parse_feed` was last called,
        sleeps until delay_seconds seconds have passed.
        """
        # If this call would violate the rate limit, sleep until it doesn't.
        if self._last_request_dt is not None:
            required = timedelta(seconds=self.delay_seconds)
            since_last_request = datetime.now() - self._last_request_dt
            if since_last_request < required:
                to_sleep = (required - since_last_request).total_seconds()
                logger.info("Sleeping: %f seconds", to_sleep)
                time.sleep(to_sleep)

        logger.info("Requesting page (first: %r, try: %d): %s", first_page, try_index, url)

        resp = self._session.get(url, headers={"user-agent": _USER_AGENT})
        self._last_request_dt = datetime.now()
        if resp.status_code != requests.codes.OK:
            raise HTTPError(url, try_index, resp.status_code)

        feed = _feed.parse(resp.content)
        if len(feed.results) == 0 and not first_page:
            raise UnexpectedEmptyPageError(url, try_index, feed)

        if feed.malformed:
            logger.warning("Malformed feed; consider handling: %s", feed.error)

        return feed


class ArxivError(Exception):
    """This package's base Exception class."""

    url: str
    """The feed URL that could not be fetched."""
    retry: int
    """
    The request try number which encountered this error; 0 for the initial try,
    1 for the first retry, and so on.
    """
    message: str
    """Message describing what caused this error."""

    def __init__(self, url: str, retry: int, message: str):
        """
        Constructs an `ArxivError` encountered while fetching the specified URL.
        """
        self.url = url
        self.retry = retry
        self.message = message
        super().__init__(self.message)

    def __reduce__(self) -> tuple:
        return (self.__class__, (self.url, self.retry, self.message))

    def __str__(self) -> str:
        return "{} ({})".format(self.message, self.url)


class UnexpectedEmptyPageError(ArxivError):
    """
    An error raised when a page of results that should be non-empty is empty.

    This should never happen in theory, but happens sporadically due to
    brittleness in the underlying arXiv API; usually resolved by retries.

    See `Client.results` for usage.
    """

    raw_feed: ParsedFeed
    """
    The raw parsed feed. Sometimes this contains useful diagnostic information,
    e.g. in `bozo_exception`.
    """

    def __init__(self, url: str, retry: int, raw_feed: ParsedFeed):
        """
        Constructs an `UnexpectedEmptyPageError` encountered for the specified
        API URL after `retry` tries.
        """
        self.url = url
        self.raw_feed = raw_feed
        super().__init__(url, retry, "Page of results was unexpectedly empty")

    def __reduce__(self) -> tuple:
        return (self.__class__, (self.url, self.retry, self.raw_feed))

    def __repr__(self) -> str:
        return "{}({}, {}, {})".format(
            _classname(self), repr(self.url), repr(self.retry), repr(self.raw_feed)
        )


class HTTPError(ArxivError):
    """
    A non-200 status encountered while fetching a page of results.

    See `Client.results` for usage.
    """

    status: int
    """The HTTP status reported by the underlying request."""

    def __init__(self, url: str, retry: int, status: int):
        """
        Constructs an `HTTPError` for the specified status code, encountered for
        the specified API URL after `retry` tries.
        """
        self.url = url
        self.status = status
        super().__init__(
            url,
            retry,
            "Page request resulted in HTTP {}".format(self.status),
        )

    def __reduce__(self) -> tuple:
        return (self.__class__, (self.url, self.retry, self.status))

    def __repr__(self) -> str:
        return "{}({}, {}, {})".format(
            _classname(self), repr(self.url), repr(self.retry), repr(self.status)
        )


def _classname(o: object) -> str:
    """A helper function for use in __repr__ methods: arxiv.Result.Link."""
    return "arxiv.{}".format(o.__class__.__qualname__)
