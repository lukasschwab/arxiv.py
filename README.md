# arxiv.py [![Python 3.6](https://img.shields.io/badge/python-3.7-blue.svg)](https://www.python.org/downloads/release/python-370/) [![PyPI](https://img.shields.io/pypi/v/arxiv)](https://pypi.org/project/arxiv/) [![GitHub Workflow Status (branch)](https://img.shields.io/github/workflow/status/lukasschwab/arxiv.py/python-lint-test/master)](https://github.com/lukasschwab/arxiv.py/actions?query=branch%3Amaster)

Python wrapper for [the arXiv API](http://arxiv.org/help/api/index).

## Quick links

+ [Full package documentation](http://lukasschwab.me/arxiv.py/index.html)
+ [Example: fetching results](#example-fetching-results): the most common usage.
+ [Example: downloading papers](#example-downloading-papers)
+ [Example: fetching results with a custom client](#example-fetching-results-with-a-custom-client)

## About arXiv

[arXiv](http://arxiv.org/) is a project by the Cornell University Library that provides open access to 1,000,000+ articles in Physics, Mathematics, Computer Science, Quantitative Biology, Quantitative Finance, and Statistics.

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
  max_results: float = float('inf'),
  sort_by: SortCriterion = SortCriterion.Relevanvce,
  sort_order: SortOrder = SortOrder.Descending
)
```

+ `query`: an arXiv query string. Advanced query formats are documented in the [arXiv API User Manual](https://arxiv.org/help/api/user-manual#query_details).
+ `id_list`: list of arXiv record IDs (typically of the format `"0710.5765v1"`). See [the arXiv API User's Manual](https://arxiv.org/help/api/user-manual#search_query_and_id_list) for documentation of the interaction between `query` and `id_list`.
+ `max_results`: The maximum number of results to be returned in an execution of this search. To fetch every result available, set `max_results=float('inf')` (default); to fetch up to 10 results, set `max_results=10`. The API's limit is 300,000 results.
+ `sort_by`: The sort criterion for results: `relevance`, `lastUpdatedDate`, or `submittedDate`.
+ `sort_order`: The sort order for results: `'descending'` or `'ascending'`.

To fetch arXiv records matching a `Search`, use `search.results()` or `(Client).results(search)` to get a generator yielding `Result`s.

#### Example: fetching results

Print the titles fo the 10 most recent articles related to the keyword "quantum:"

```python
import arxiv

search = arxiv.Search(
  query = "quantum",
  max_results = 10,
  sort_by = arxiv.SortCriterion.SubmittedDate
)

for result in search.results():
  print(result.title)
```

Fetch and print the title of the paper with ID "1605.08386v1:"

```python
import arxiv

search = arxiv.Search(id_list=["1605.08386v1"])
paper = next(search.results())
print(paper.title)
```

### Result

<!-- TODO: improve this section. -->

The `Result` objects yielded by `(Search).results()` include metadata about each paper and some helper functions for downloading their content.

The meaning of the underlying raw data is documented in the [arXiv API User Manual: Details of Atom Results Returned](https://arxiv.org/help/api/user-manual#_details_of_atom_results_returned).

+ `result.entry_id`: A url `http://arxiv.org/abs/{id}`.
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

paper = next(arxiv.Search(id_list=["1605.08386v1"]).results())
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

paper = next(arxiv.Search(id_list=["1605.08386v1"]).results())
# Download the archive to the PWD with a default filename.
paper.download_source()
# Download the archive to the PWD with a custom filename.
paper.download_source(filename="downloaded-paper.tar.gz")
# Download the archive to a specified directory with a custom filename.
paper.download_source(dirpath="./mydir", filename="downloaded-paper.tar.gz")
```

### Client

A `Client` specifies a strategy for fetching results from arXiv's API; it obscures pagination and retry logic.

For most use cases the default client should suffice. You can construct it explicitly with `arxiv.Client()`, or use it via the `(Search).results()` method.

```python
arxiv.Client(
  page_size: int = 100,
  delay_seconds: int = 3,
  num_retries: int = 3
)
```

+ `page_size`: the number of papers to fetch from arXiv per page of results. Smaller pages can be retrieved faster, but may require more round-trips. The API's limit is 2000 results.
+ `delay_seconds`: the number of seconds to wait between requests for pages. [arXiv's Terms of Use](https://arxiv.org/help/api/tou) ask that you "make no more than one request every three seconds."
+ `num_retries`: The number of times the client will retry a request that fails, either with a non-200 HTTP status code or with an unexpected number of results given the search parameters.

#### Example: fetching results with a custom client

`(Search).results()` uses the default client settings. If you want to use a client you've defined instead of the defaults, use `(Client).results(...)`:

```python
import arxiv

big_slow_client = arxiv.Client(
  page_size = 1000,
  delay_seconds = 10,
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
>>> logging.basicConfig(level=logging.INFO)
>>> paper = next(arxiv.Search(id_list=["1605.08386v1"]).results())
INFO:arxiv.arxiv:Requesting 100 results at offset 0
INFO:arxiv.arxiv:Requesting page of results
INFO:arxiv.arxiv:Got first page; 1 of inf results available
```
