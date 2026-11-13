"""Behavioral checks for the real lxml objects behind the feed parser's protocol."""

from datetime import datetime, timezone
from pathlib import Path

import pytest
from lxml import etree

from arxiv import _feed


_TREE = (
    b'<root xmlns:t="urn:test" xmlns:a="urn:attributes">'
    b'<t:child present="value" empty="" a:key="namespaced">first'
    b"<t:nested>deep</t:nested></t:child>"
    b"<t:child/><t:child>last</t:child></root>"
)
_FEED = b"""<feed xmlns="http://www.w3.org/2005/Atom"
    xmlns:arxiv="http://arxiv.org/schemas/atom"
    xmlns:opensearch="http://a9.com/-/spec/opensearch/1.1/">
  <opensearch:totalResults> 12 </opensearch:totalResults>
  <opensearch:startIndex>3</opensearch:startIndex>
  <opensearch:itemsPerPage>1</opensearch:itemsPerPage>
  <entry>
    <id>http://arxiv.org/abs/1234.56789v1</id>
    <updated>2025-01-02T03:04:05Z</updated>
    <published>2025-01-01T03:04:05Z</published>
    <title> A   contract
      test </title>
    <summary>Summary</summary>
    <author><name>Ada</name><arxiv:affiliation>Lab</arxiv:affiliation>
      <arxiv:affiliation/><arxiv:affiliation>University</arxiv:affiliation></author>
    <author><name>Grace</name></author>
    <link href="https://example.org/paper" title="" rel="alternate" type="text/html"/>
    <link href="https://example.org/paper.pdf" title="pdf" type="application/pdf"/>
    <link title="missing href"/>
    <category term="cs.AI"/><category term=""/><category/>
    <arxiv:primary_category term="cs.AI"/>
  </entry>
</feed>"""


@pytest.mark.parametrize("content", [_TREE, bytearray(_TREE)], ids=["bytes", "bytearray"])
def test_element_contract(content: bytes | bytearray) -> None:
    root = _feed._parse_xml(content)
    assert root is not None
    assert root.text is None
    namespaces = {"t": "urn:test"}
    iterator = root.iterfind("t:child", namespaces)
    assert iter(iterator) is iterator
    first = next(iterator)
    assert root.find("t:child", namespaces) is first
    remaining = list(iterator)
    assert [child.text for child in remaining] == [None, "last"]
    assert root.find("t:child[2]", namespaces) is remaining[0]
    assert root.find("child", namespaces) is None
    assert next(iterator, None) is None
    assert first.text == "first" and type(first.text) is str
    assert first.get("present") == "value" and type(first.get("present")) is str
    assert first.get("empty") == "" and type(first.get("empty")) is str
    assert first.get("{urn:attributes}key") == "namespaced"
    assert type(first.get("{urn:attributes}key")) is str
    assert first.get("key") is None
    assert first.get("missing") is None
    nested = first.find("t:nested", namespaces)
    assert nested is not None
    assert nested.text == "deep" and type(nested.text) is str
    nested_iterator = first.iterfind("t:nested", namespaces)
    assert iter(nested_iterator) is nested_iterator
    assert list(nested_iterator) == [nested]
    for element in [root, first, *remaining, nested]:
        assert element.find("t:missing", namespaces) is None
        missing = element.iterfind("t:missing", namespaces)
        assert iter(missing) is missing
        assert list(missing) == []
        assert element.get("missing") is None
    assert remaining[0].text is None
    assert remaining[1].text == "last" and type(remaining[1].text) is str


def test_parse_preserves_namespaced_feed_fields() -> None:
    feed = _feed.parse(_FEED)
    assert feed.malformed is False and feed.error is None
    assert feed.header == _feed.FeedHeader(total_results=12, items_per_page=1, start_index=3)
    assert len(feed.results) == 1
    result = feed.results[0]
    assert result.entry_id == "http://arxiv.org/abs/1234.56789v1"
    assert result.title == " A contract test "
    assert result.summary == "Summary"
    assert result.updated == datetime(2025, 1, 2, 3, 4, 5, tzinfo=timezone.utc)
    assert result.published == datetime(2025, 1, 1, 3, 4, 5, tzinfo=timezone.utc)
    assert [(a.name, a.affiliation) for a in result.authors] == [
        ("Ada", ["Lab", "University"]),
        ("Grace", []),
    ]
    assert [(link.href, link.title, link.rel, link.content_type) for link in result.links] == [
        ("https://example.org/paper", "", "alternate", "text/html"),
        ("https://example.org/paper.pdf", "pdf", "", "application/pdf"),
    ]
    assert result.primary_category == "cs.AI"
    assert result.categories == ["cs.AI", ""]


def test_empty_recovery_returns_none() -> None:
    # Whitespace recovers to no root; truly empty bytes raise XMLSyntaxError.
    assert _feed._parse_xml(b" ") is None
    feed = _feed.parse(b" ")
    assert feed.malformed is True and isinstance(feed.error, ValueError)
    assert feed.results == [] and feed.header == _feed.FeedHeader()


def test_empty_document_syntax_error_is_reported() -> None:
    with pytest.raises(etree.XMLSyntaxError):
        _feed._parse_xml(b"")
    feed = _feed.parse(b"")
    assert feed.malformed is True and isinstance(feed.error, etree.XMLSyntaxError)
    assert feed.results == [] and feed.header == _feed.FeedHeader()


def test_malformed_document_is_recovered() -> None:
    content = _FEED.removesuffix(b"</feed>")
    assert _feed._parse_xml(content) is not None
    recovered = _feed.parse(content)
    assert recovered.malformed is False and recovered.error is None
    assert recovered.header == _feed.parse(_FEED).header
    assert len(recovered.results) == 1
    assert recovered.results[0].summary == "Summary"


@pytest.mark.parametrize("external", [False, True], ids=["internal", "external-file"])
def test_entities_are_not_expanded(tmp_path: Path, external: bool) -> None:
    secret = "ENTITY_EXPANSION_MUST_NOT_APPEAR"
    secret_file = tmp_path / "secret.txt"
    secret_file.write_text(secret, encoding="utf-8")
    definition = f'SYSTEM "{secret_file.as_uri()}"' if external else f'"{secret}"'
    doctype = f"<!DOCTYPE feed [<!ENTITY secret {definition}>]>".encode()
    content = doctype + _FEED.replace(b"Summary", b"&secret;")
    root = _feed._parse_xml(content)
    assert root is not None
    summary = root.find("atom:entry/atom:summary", {"atom": "http://www.w3.org/2005/Atom"})
    assert summary is not None and summary.text is None
    feed = _feed.parse(content)
    assert feed.malformed is False and feed.error is None
    assert len(feed.results) == 1
    assert feed.results[0].summary == ""
