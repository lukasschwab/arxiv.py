from __future__ import print_function
import logging
import time
import re
import feedparser

try:
    # Python 2
    from urllib import urlencode
    from urllib import urlretrieve
except ImportError:
    # Python 3
    from urllib.parse import urlencode
    from urllib.request import urlretrieve

logger = logging.getLogger(__name__)


class Search(object):
    """
    Class to search and download abstracts from the arXiv

    Args:
        query (string):
        id_list (list): List of arXiv object IDs.
        max_results (int): The maximum number of abstracts that should be downloaded. Defaults to
            infinity, i.e., no limit at all.
        start (int): The offset of the first returned object from the arXiv query results.
        sort_by (string): The arXiv field by which the result should be sorted.
        sort_order (string): The sorting order, i.e. "ascending", "descending" or None.
        max_chunk_results (int): Internally, a arXiv search query is split up into smaller
            queries that download the data iteratively in chunks. This parameter sets an upper
            bound on the number of abstracts to be retrieved in a single internal request.
        time_sleep (int): Time (in seconds) between two subsequent arXiv REST calls. Defaults to
            :code:`3`, the recommendation of arXiv.
        prune (bool): Whether some of the values in each response object should be dropped.
            Defaults to True.

    """

    root_url = 'http://export.arxiv.org/api/'
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
        'id']

    def __init__(self, query=None, id_list=None, max_results=None, start=0, sort_by=None,
                 sort_order=None, max_chunk_results=None, time_sleep=3, prune=True):

        self.query = query
        self.id_list = id_list
        self.sort_by = sort_by
        self.sort_order = sort_order
        self.max_chunk_results = max_chunk_results
        self.time_sleep = time_sleep
        self.prune = prune
        self.max_results = max_results
        self.start = start

        if not self.max_results:
            logger.info('max_results defaulting to inf.')
            self.max_results = float('inf')

    def _get_url(self, start=0, max_results=None):

        url_args = urlencode(
            {
                "search_query": self.query,
                "id_list": self.id_list,
                "start": start,
                "max_results": max_results,
                "sortBy": self.sort_by,
                "sortOrder": self.sort_order
            }
        )

        return self.root_url + 'query?' + url_args

    def _parse(self, url):
        """
        Downloads the data provided by the REST endpoint given in the url.
        """
        result = feedparser.parse(url)

        if result.get('status') != 200:
            logger.error(
                "HTTP Error {} in query".format(result.get('status', 'no status')))
            return []
        return result['entries']

    def _prune_result(self, result):
        """
        Deletes some of the keys from the downloaded result.
        """

        for key in self.prune_keys:
            try:
                del result['key']
            except KeyError:
                pass

        return result

    def _process_result(self, result):

        # Useful to have for download automation
        result['pdf_url'] = None
        for link in result['links']:
            if 'title' in link and link['title'] == 'pdf':
                result['pdf_url'] = link['href']
        result['affiliation'] = result.pop('arxiv_affiliation', 'None')

        result['arxiv_url'] = result.pop('link')
        result['title'] = result['title'].rstrip('\n')
        result['summary'] = result['summary'].rstrip('\n')
        result['authors'] = [d['name'] for d in result['authors']]
        if 'arxiv_comment' in result:
            result['arxiv_comment'] = result['arxiv_comment'].rstrip('\n')
        else:
            result['arxiv_comment'] = None
        if 'arxiv_journal_ref' in result:
            result['journal_reference'] = result.pop('arxiv_journal_ref')
        else:
            result['journal_reference'] = None
        if 'arxiv_doi' in result:
            result['doi'] = result.pop('arxiv_doi')
        else:
            result['doi'] = None

        if self.prune:
            result = self._prune_result(result)

        return result

    def _get_next(self):

        n_left = self.max_results
        start = self.start

        while n_left > 0:

            if n_left < self.max_results:
                logger.info('... play nice on the arXiv and sleep a bit ...')
                time.sleep(self.time_sleep)

            logger.info('Fetch from arxiv ({} results left to download)'.format(n_left))
            url = self._get_url(
                start=start,
                max_results=min(n_left, self.max_chunk_results))

            results = self._parse(url)

            # Update the entries left to download
            n_fetched = len(results)
            logger.info('Received {} entries'.format(n_fetched))

            if n_fetched == 0:
                logger.info('No more entries left to fetch.')
                logger.info('Fetching finished.')
                break

            # Update the number of results left to download
            n_left = n_left - n_fetched
            start = start + n_fetched

            # Process results
            results = [self._process_result(r) for r in results if r.get("title", None)]

            yield results

    def download(self, iterative=False):
        """
        Triggers the download of the result of the given search query.

        Args:
            iterative (bool): If true, then an iterator is returned, which allows to download the
                data iteratively. Otherwise, all the data is fetched first and then returned.

        Returns:
            iterable: Either a list or a general iterator holding the result of the search query.
        """
        logger.info('Start downloading')
        if iterative:

            logger.info('Build iterator')

            def iterator():
                logger.info('Start iterating')
                for result in self._get_next():
                    for entry in result:
                        yield entry
            return iterator
        else:
            results = list()
            for result in self._get_next():
                # Only append result if title is not empty
                results = results + result
            return results


def query(query="", id_list=[], prune=True, max_results=None, start=0, sort_by="relevance",
          sort_order="descending", max_chunk_results=1000, iterative=False):
    """
    See :py:class:`arxiv.Search` for a description of the parameters.
    """

    search = Search(
        query=query,
        id_list=','.join(id_list),
        sort_by=sort_by,
        sort_order=sort_order,
        prune=prune,
        max_results=max_results,
        start = start,
        max_chunk_results=max_chunk_results)

    return search.download(iterative=iterative)


def slugify(obj):
    # Remove special characters from object title
    filename = '_'.join(re.findall(r'\w+', obj.get('title', 'UNTITLED')))
    # Prepend object id
    filename = "%s.%s" % (obj.get('pdf_url').split('/')[-1], filename)
    return filename


def download(obj, dirpath='./', slugify=slugify):
    if not obj.get('pdf_url', ''):
        print("Object has no PDF URL.")
        return
    if dirpath[-1] != '/':
        dirpath += '/'
    path = dirpath + slugify(obj) + '.pdf'
    urlretrieve(obj['pdf_url'], path)
    return path
