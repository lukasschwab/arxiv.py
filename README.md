# arxiv.py
Python wrapper for the arXiv API: http://arxiv.org/help/api/index

## About arXiv
[arXiv](http://arxiv.org/) is a project by the Cornell University Library that provides open access to 1,000,000+ articles in Physics, Mathematics, Computer Science, Quantitative Biology, Quantitative Finance, and Statistics.

They have [an API](http://arxiv.org/help/api/index) that uses ATOM feeds to serve simple database queries.
Unfortunately, handling these ATOM requsts can be clumsy (especially given inconsistency in data between different result objects, even in the same query).
This is where arxiv.py comes it: it constructs requests for arXiv and gets ATOM feeds via a simple handful of methods, and parses the results into an intuitive format.

Cool demos hopefully coming soon!

## Docs

To get the arxiv package, simply run `pip install arxiv` at the command line.

At the beginning of your Python script, include the line `import arxiv`.

### Query

`arxiv.query(s, prune=True, start=0, max_results=10)`

Sends arXiv a simple query, and returns a list of results, each of which is a `dict` representing an article that matches the query. The articles are ordered for relevance by arXiv.

+ When bool `prune` is `True` (default), a number of artifacts of the ATOM-to-dict conversion are removed from each result to isolate the useful fields. When `prune` is `False`, `prune_query_result` is not called and those key/value pairs are not removed.
+ Integer `start` identifies a 0-indexed position where the query results begin. For example, `query('term', start=4)` will only request and return results indexed 4-14.
+ Integer `max_results` identifies the number of results to be returned (thus, `query` will return results at positions `start` through `start + max_results`). There are some upper limits involved; if you want to pull >60,000 results at a time you should look at the arXiv [API documentation](http://arxiv.org/help/api/user-manual).

### Clean query results

`arxiv.mod_query_result(result)`

Takes a query result dict representing an article and modifies some keys and values to be more user-readable.
See code for specifics.

`arxiv.prune_query_result(result)`

Takes a query result dict representing an article and removes some keys that are redundant or useless.
See code for specifics.

### Download PDF

`arxiv.download(obj)`

Looks up keys `pdf_url` and `title` on dict `obj`. Downloads the PDF from `pdf_url` and saves it to {title}.pdf in the present working directory.