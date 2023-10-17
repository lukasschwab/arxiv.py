# arxiv.py
[![PyPI](https://img.shields.io/pypi/v/arxiv)](https://pypi.org/project/arxiv/) ![PyPI - Python Version](https://img.shields.io/pypi/pyversions/arxiv) [![GitHub Workflow Status (branch)](https://img.shields.io/github/actions/workflow/status/lukasschwab/arxiv.py/python-package.yml?branch=master)](https://github.com/lukasschwab/arxiv.py/actions?query=branch%3Amaster)

Python wrapper for [the arXiv API](https://arxiv.org/help/api/index).

## Quick links

+ [Full package documentation](https://lukasschwab.me/arxiv.py/index.html)
+ [Example: fetching results](#example-fetching-results): the most common usage.
+ [Example: downloading papers](#example-downloading-papers)
+ [Example: fetching results with a custom client](#example-fetching-results-with-a-custom-client)

## About arXiv

[arXiv](https://arxiv.org/) is a project by the Cornell University Library that provides open access to 1,000,000+ articles in Physics, Mathematics, Computer Science, Quantitative Biology, Quantitative Finance, and Statistics.

## Usage

### Installation

```bash
$ pip install arxiv
```

In your Python script, include the line

```python
import arxiv
```

### Search

A `Search` specifies a search of arXiv's database.

```python
arxiv.Search(
  query: str = "",
  id_list: List[str] = [],
  max_results: int | None = None,
  sort_by: SortCriterion = SortCriterion.Relevance,
  sort_order: SortOrder = SortOrder.Descending
)
```

+ `query`: an arXiv query string. Advanced query formats are documented in the [arXiv API User Manual](https://arxiv.org/help/api/user-manual#query_details).
+ `id_list`: list of arXiv record IDs (typically of the format `"0710.5765v1"`). See [the arXiv API User's Manual](https://arxiv.org/help/api/user-manual#search_query_and_id_list) for documentation of the interaction between `query` and `id_list`.
+ `max_results`: The maximum number of results to be returned in an execution of this search. To fetch every result available, set `max_results=None` (default); to fetch up to 10 results, set `max_results=10`. The API's limit is 300,000 results.
+ `sort_by`: The sort criterion for results: `relevance`, `lastUpdatedDate`, or `submittedDate`.
+ `sort_order`: The sort order for results: `'descending'` or `'ascending'`.

To fetch arXiv records matching a `Search`, use `(Client).results(search)` to get a generator yielding `Result`s.

#### Example: fetching results

Print the titles fo the 10 most recent articles related to the keyword "quantum:"

```python
import arxiv

search = arxiv.Search(
  query = "quantum",
  max_results = 10,
  sort_by = arxiv.SortCriterion.SubmittedDate
)

for result in arxiv.Client().results(search):
  print(result.title)
```

Fetch and print the title of the paper with ID "1605.08386v1:"

```python
import arxiv

client = arxiv.Client()
search = arxiv.Search(id_list=["1605.08386v1"])

paper = next(arxiv.Client().results(search))
print(paper.title)
```

### Result

<!-- TODO: improve this section. -->

The `Result` objects yielded by `(Client).results()` include metadata about each paper and some helper functions for downloading their content.

The meaning of the underlying raw data is documented in the [arXiv API User Manual: Details of Atom Results Returned](https://arxiv.org/help/api/user-manual#_details_of_atom_results_returned).

+ `result.entry_id`: A url `https://arxiv.org/abs/{id}`.
+ `result.updated`: When the result was last updated.
+ `result.published`: When the result was originally published.
+ `result.title`: The title of the result.
+ `result.authors`: The result's authors, as `arxiv.Author`s.
+ `result.summary`: The result abstract.
+ `result.comment`: The authors' comment if present.
+ `result.journal_ref`: A journal reference if present.
+ `result.doi`: A URL for the resolved DOI to an external resource if present.
+ `result.primary_category`: The result's primary arXiv category. See [arXiv: Category Taxonomy](https://arxiv.org/category_taxonomy).
+ `result.categories`: All of the result's categories. See [arXiv: Category Taxonomy](https://arxiv.org/category_taxonomy).
+ `result.links`: Up to three URLs associated with this result, as `arxiv.Link`s.
+ `result.pdf_url`: A URL for the result's PDF if present. Note: this URL also appears among `result.links`.

They also expose helper methods for downloading papers: `(Result).download_pdf()` and `(Result).download_source()`.

#### Example: downloading papers

To download a PDF of the paper with ID "1605.08386v1," run a `Search` and then use `(Result).download_pdf()`:

```python
import arxiv

paper = next(arxiv.Client().results(arxiv.Search(id_list=["1605.08386v1"])))
# Download the PDF to the PWD with a default filename.
paper.download_pdf()
# Download the PDF to the PWD with a custom filename.
paper.download_pdf(filename="downloaded-paper.pdf")
# Download the PDF to a specified directory with a custom filename.
paper.download_pdf(dirpath="./mydir", filename="downloaded-paper.pdf")
```

The same interface is available for downloading .tar.gz files of the paper source:

```python
import arxiv

paper = next(arxiv.Client().results(arxiv.Search(id_list=["1605.08386v1"])))
# Download the archive to the PWD with a default filename.
paper.download_source()
# Download the archive to the PWD with a custom filename.
paper.download_source(filename="downloaded-paper.tar.gz")
# Download the archive to a specified directory with a custom filename.
paper.download_source(dirpath="./mydir", filename="downloaded-paper.tar.gz")
```

### Client

A `Client` specifies a strategy for fetching results from arXiv's API; it obscures pagination and retry logic. For most use cases the default client should suffice.

```python
# Default client properties.
arxiv.Client(
  page_size: int = 100,
  delay_seconds: float = 3.0,
  num_retries: int = 3
)
```

+ `page_size`: the number of papers to fetch from arXiv per page of results. Smaller pages can be retrieved faster, but may require more round-trips. The API's limit is 2000 results.
+ `delay_seconds`: the number of seconds to wait between requests for pages. [arXiv's Terms of Use](https://arxiv.org/help/api/tou) ask that you "make no more than one request every three seconds."
+ `num_retries`: The number of times the client will retry a request that fails, either with a non-200 HTTP status code or with an unexpected number of results given the search parameters.

#### Example: fetching results with a custom client

```python
import arxiv

big_slow_client = arxiv.Client(
  page_size = 1000,
  delay_seconds = 10.0,
  num_retries = 5
)

# Prints 1000 titles before needing to make another request.
for result in big_slow_client.results(arxiv.Search(query="quantum")):
  print(result.title)
```

#### Example: logging

To inspect this package's network behavior and API logic, configure an `INFO`-level logger.

```pycon
>>> import logging, arxiv
>>> logging.basicConfig(level=logging.DEBUG)
>>> client = arxiv.Client()
>>> paper = next(client.results(arxiv.Search(id_list=["1605.08386v1"])))
INFO:arxiv.arxiv:Requesting 100 results at offset 0
INFO:arxiv.arxiv:Requesting page (first: False, try: 0): https://export.arxiv.org/api/query?search_query=&id_list=1605.08386v1&sortBy=relevance&sortOrder=descending&start=0&max_results=100
DEBUG:urllib3.connectionpool:Starting new HTTPS connection (1): export.arxiv.org:443
DEBUG:urllib3.connectionpool:https://export.arxiv.org:443 "GET /api/query?search_query=&id_list=1605.08386v1&sortBy=relevance&sortOrder=descending&start=0&max_results=100&user-agent=arxiv.py%2F1.4.8 HTTP/1.1" 200 979
```
