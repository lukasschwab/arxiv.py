"""Internal lxml-based Atom feed parser for the arXiv API.

Replaces a prior `feedparser` dependency. The arXiv API returns well-formed
Atom 1.0 with three custom namespaces (`arxiv:`, `opensearch:`, and `dc:`),
so a thin namespace-aware lxml parser gives us:

+ Direct access to extension elements like `<arxiv:affiliation>` nested inside
  `<author>`, which feedparser collapses (see issues kurtmckee/feedparser#24,
  kurtmckee/feedparser#145, and lukasschwab/arxiv.py#62).
+ Substantially faster parsing than feedparser.
+ No reliance on feedparser's HTML-sanitizing / bozo machinery, which is
  unnecessary for arXiv's well-formed responses.

The public surface is intentionally minimal: `parse(content)` returns a
`ParsedFeed` carrying the page header plus a list of fully-constructed
`arxiv.Result` objects.

For the response format see
https://info.arxiv.org/help/api/user-manual.html#_details_of_atom_results_returned.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from lxml import etree

if TYPE_CHECKING:
    from . import Result

logger = logging.getLogger(__name__)

# Namespaces declared by the arXiv API. Documented at
# https://info.arxiv.org/help/api/user-manual.html#_details_of_atom_results_returned
_NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "arxiv": "http://arxiv.org/schemas/atom",
    "opensearch": "http://a9.com/-/spec/opensearch/1.1/",
}


def _text(elem: Any, path: str) -> str | None:
    if elem is None:
        return None
    found = elem.find(path, _NS)
    if found is None or found.text is None:
        return None
    return found.text


def _parse_datetime(s: str | None) -> datetime | None:
    """Parse an Atom RFC 3339 timestamp into a tz-aware UTC datetime."""
    if s is None:
        return None
    # arXiv emits e.g. "2016-05-26T17:59:46Z". `fromisoformat` handles
    # `+00:00` natively; swap `Z` for that on older Pythons.
    text = s.strip().replace("Z", "+00:00")
    dt = datetime.fromisoformat(text)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


@dataclass
class FeedHeader:
    """Page-level metadata from the opensearch elements at the top of a feed."""

    total_results: int = 0
    items_per_page: int = 0
    start_index: int = 0


@dataclass
class ParsedFeed:
    """A parsed arXiv API response."""

    header: FeedHeader
    results: list["Result"] = field(default_factory=list)
    malformed: bool = False
    error: Exception | None = None


def _build_result(entry: Any) -> "Result | None":
    """Convert a parsed `<entry>` element into a `Result`, or None if invalid."""
    # Imported lazily to avoid a circular import; `Result` lives in `arxiv`.
    from . import Result

    entry_id = _text(entry, "atom:id")
    if not entry_id:
        logger.warning("Skipping entry without <id>")
        return None

    updated = _parse_datetime(_text(entry, "atom:updated"))
    published = _parse_datetime(_text(entry, "atom:published"))
    if updated is None or published is None:
        missing = "updated" if updated is None else "published"
        logger.warning("Skipping entry %s missing <%s>", entry_id, missing)
        return None

    title = _text(entry, "atom:title") or ""

    authors: list[Result.Author] = []
    for a in entry.iterfind("atom:author", _NS):
        name = _text(a, "atom:name") or ""
        affiliations = [
            af.text for af in a.iterfind("arxiv:affiliation", _NS) if af.text is not None
        ]
        authors.append(Result.Author(name=name, affiliation=affiliations))

    links: list[Result.Link] = []
    for link in entry.iterfind("atom:link", _NS):
        href = link.get("href")
        if href is None:
            continue
        links.append(
            Result.Link(
                href=href,
                title=link.get("title"),
                rel=link.get("rel") or "",
                content_type=link.get("type"),
            )
        )

    categories: list[str] = []
    for cat in entry.iterfind("atom:category", _NS):
        term = cat.get("term")
        if term is not None:
            categories.append(term)

    primary_elem = entry.find("arxiv:primary_category", _NS)
    primary_category = primary_elem.get("term") if primary_elem is not None else ""

    return Result(
        entry_id=entry_id,
        updated=updated,
        published=published,
        title=re.sub(r"\s+", " ", title),
        authors=authors,
        summary=_text(entry, "atom:summary") or "",
        comment=_text(entry, "arxiv:comment"),
        journal_ref=_text(entry, "arxiv:journal_ref"),
        doi=_text(entry, "arxiv:doi"),
        primary_category=primary_category or "",
        categories=categories,
        links=links,
    )


def parse(content: bytes) -> ParsedFeed:
    """Parse an arXiv API Atom response.

    Always returns a `ParsedFeed`. If the document is unparseable, returns an
    empty feed with `malformed=True` and `error` set. Individual entries that
    are missing required fields are logged and skipped.
    """
    if not isinstance(content, (bytes, bytearray)):
        raise TypeError("parse expects bytes")

    try:
        # Disable network access and entity expansion; arXiv responses never
        # need to reference external resources.
        parser = etree.XMLParser(
            resolve_entities=False,
            no_network=True,
            huge_tree=False,
            recover=True,
        )
        root = etree.fromstring(content, parser=parser)
    except etree.XMLSyntaxError as exc:
        return ParsedFeed(header=FeedHeader(), results=[], malformed=True, error=exc)

    if root is None:
        return ParsedFeed(
            header=FeedHeader(),
            results=[],
            malformed=True,
            error=ValueError("empty document"),
        )

    def _int(path: str) -> int:
        text = _text(root, path)
        if text is None:
            return 0
        try:
            return int(text.strip())
        except ValueError:
            return 0

    header = FeedHeader(
        total_results=_int("opensearch:totalResults"),
        items_per_page=_int("opensearch:itemsPerPage"),
        start_index=_int("opensearch:startIndex"),
    )

    results: list["Result"] = []
    for entry_elem in root.iterfind("atom:entry", _NS):
        result = _build_result(entry_elem)
        if result is not None:
            results.append(result)

    return ParsedFeed(header=header, results=results, malformed=False)
