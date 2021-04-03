import logging, re, os

from datetime import datetime
from urllib.request import urlretrieve
from typing import List

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
        updated=datetime.now(),
        published=datetime.now(),
        title="",
        authors=[],
        summary="",
        comment="",
        primary_category="",
        categories=[],
        links=[]
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

    def _from_feed_entry(entry):
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
    
    def get_short_id(self):
        """
        Returns the short ID for this result. If the result URL is
        `"http://arxiv.org/abs/quant-ph/0201082v1"`, `result.get_short_id()`
        returns `"0201082v1"`.
        """
        return self.entry_id.split('/')[-1]
    
    def get_pdf_url(self):
        """
        Returns the URL of a PDF version of this result.
        """
        pdf_links = [l.href for l in self.links if l.title == 'pdf']
        if len(pdf_links) == 0:
            raise ValueError("Result does not have a PDF link")
        elif len(pdf_links) > 1:
            logger.warn("%s has multiple PDF links; using %s", self.get_short_id(), pdf_links[0].href)
        return pdf_links[0]

    def _get_default_filename(self, extension="pdf"):
        """
        A default `to_filename` function for the extension given.
        """
        nonempty_title = self.title if self.title else "UNTITLED"
        # Remove disallowed characters.
        clean_title = '_'.join(re.findall(r'\w+', nonempty_title))
        return "{}.{}.{}".format(self.get_short_id(), clean_title, extension)

    def download_pdf(self, dirpath='./', filename=None):
        """
        Downloads the PDF for this result to the specified directory. The
        filename is generated by calling `to_filename(self)`.
        """
        if not filename:
            filename = self._get_default_filename()
        path = os.path.join(dirpath, filename)
        written_path, _ = urlretrieve(self.get_pdf_url(), path)
        return written_path

    def download_source(self, dirpath='./', filename=None):
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
        def __init__(self, entry_author):
            self.name = entry_author.name

    class Link(object):
        """
        A light inner class for representing a result's links.
        """
        href: str
        title: str
        rel: str
        content_type: str
        def __init__(self, feed_link):
            self.href = feed_link.href
            self.title = feed_link.get('title')
            self.rel = feed_link.get('rel')
            self.content_type = feed_link.get('content_type')