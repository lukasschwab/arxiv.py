# http://arxiv.org/help/api/user-manual#extension_elements

import feedparser
root_url = 'http://export.arxiv.org/api/'

# TODO: Field queries ("Details of Query Construction")
# TODO: Do I want to support boolean operators?
# TODO: Do I want to add support for quotes to group words?
def query(s, prune=True, start=0, max_results=10):
	# TODO: Error parsing here; abstract to own method?
	# TODO: Some kind of a results paging interface, modifying start val
	# Gets a list of top results, each of which is a dict
	results = feedparser.parse(root_url + 'query?search_query=all:' + s + '&start=' + str(start) + '&max_results=' + str(results))['entries']

	for result in results:
		# Renamings and modifications
		mod_query_result(result)
		if prune:
			prune_query_result(result)

	return results


def mod_query_result(result):
	# Useful to have for download automation
	# Need to test if list is this long
	# result['pdf_url'] = result['links'][2]['href']

	result['affiliation'] = result.pop('arxiv_affiliation', 'None')
	result['arxiv_url'] = result.pop('link')
	result['summary'] = result['summary'].rstrip('\n')
	result['authors'] = [d['name'] for d in result['authors']]

	# TODO: Parse this? pagecount, figure count, table count
	# 		Might not be reliable
	try:
		result['arxiv_comment'] = result['arxiv_comment'].rstrip('\n')
	except KeyError:
		pass
	try:
		result['journal_reference'] = result.pop('arxiv_journal_ref')
	except KeyError:
		pass
	try:
		result['doi'] = result.pop('arxiv_doi')
	except KeyError:
		pass


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
	try:
		urllib.urlretrieve(obj['pdf_url'],"/Users/lukas/Desktop/"+obj['title']+".pdf")
	except KeyError:
		print obj + " has no key 'pdf_url' or no key 'title'"