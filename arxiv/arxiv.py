# http://arxiv.org/help/api/user-manual#extension_elements

import feedparser
root_url = 'http://export.arxiv.org/api/'

# TODO: Field queries ("Details of Query Construction")
# TODO: Do I want to support boolean operators?
# TODO: Do I want to add support for quotes to group words/order of ops?
def query(s, prune=True, start=0, max_results=10):
	# Gets a list of top results, each of which is a dict
	results = feedparser.parse(root_url + 'query?search_query=all:' + s + '&start=' + str(start) + '&max_results=' + str(max_results))
	if results['status'] != 200:
		# TODO: better error reporting
		raise Exception('Error', results['status'])
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


def download(obj):
	# Downloads file in obj (can be result or unique page) if it has a .pdf link
	import urllib
	if 'pdf_url' in obj and 'title' in obj and obj['pdf_url'] and obj['title']:
		urllib.urlretrieve(obj['pdf_url'],obj['title']+".pdf")
	else:
		print "Object passed in has no PDF URL, or has no title"