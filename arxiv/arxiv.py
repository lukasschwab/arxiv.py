from __future__ import print_function
from requests.exceptions import HTTPError

try:
    # Python 2
    from urllib import quote_plus
    from urllib import urlencode
    from urllib import urlretrieve
except ImportError:
    # Python 3
    from urllib.parse import quote_plus
    from urllib.parse import urlencode
    from urllib.request import urlretrieve
import feedparser

root_url = 'http://export.arxiv.org/api/'

def query(search_query="", 
         id_list=[], 
         prune=True, 
         start=0, 
         max_results=10, 
         sort_by="relevance", 
         sort_order="descending"):
    url_args = urlencode({"search_query": search_query, 
                          "id_list": ','.join(id_list),
                          "start": start,
                          "max_results": max_results,
                          "sortBy": sort_by,
                          "sortOrder": sort_order})
    results = feedparser.parse(root_url + 'query?' + url_args)
    if results.get('status') != 200:
        # TODO: better error reporting
        raise Exception("HTTP Error " + str(results.get('status', 'no status')) + " in query")
    else:
        results = results['entries']
    for result in results:
        # Renamings and modifications
        mod_query_result(result)
        if prune:
            prune_query_result(result)
    return results

def mod_query_result(result):
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

def prune_query_result(result):
    prune_keys = ['updated_parsed',
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
    for key in prune_keys:
        try:
            del result['key']
        except KeyError:
            pass

def to_slug(title):
    # Remove special characters
    filename = ''.join(c if c.isalnum() else '_' for c in title)
    # delete duplicate underscores
    filename = '_'.join(list(filter(None, filename.split('_'))))
    return filename

def download(obj, dirname='./', prepend_id=False, slugify=False):
    # Downloads file in obj (can be result or unique page) if it has a .pdf link
    if 'pdf_url' in obj and 'title' in obj and obj['pdf_url'] and obj['title']:
        filename = obj['title']
        if slugify:
            filename = to_slug(filename)
        if prepend_id:
            filename = obj['arxiv_url'].split('/')[-1] + '-' + filename
        filename = dirname + filename + '.pdf'
        # Download
        urlretrieve(obj['pdf_url'], filename)
        return filename
    else:
        print("Object obj has no PDF URL, or has no title")
