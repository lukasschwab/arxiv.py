# arxiv.py
Python wrapper for the arXiv API: http://arxiv.org/help/api/index

## About arXiv
[arXiv](http://arxiv.org/) is a project by the Cornell University Library that provides open access to 1,000,000+ articles in Physics, Mathematics, Computer Science, Quantitative Biology, Quantitative Finance, and Statistics.

They have [an API](http://arxiv.org/help/api/index) that uses ATOM feeds to serve simple database queries.
Unfortunately, handling these ATOM requsts can be clumsy (especially given inconsistency in data between different result objects, even in the same query).
This is where arxiv.py comes it: it constructs requests for arXiv and gets ATOM feeds via a simple handful of methods, and parses the results into an intuitive format.

## Usage

### Installation

```bash
$ pip install arxiv
```

In your Python script, include the line

```python
import arxiv
```

Verify the installation with

```bash
$ python setup.py test


### Query

```python
arxiv.query(search_query, id_list, prune, start, max_results, sort_by, sort_order)
```

| **Argument**   | **Type**        | **Default**    | **Required?** |
|----------------|-----------------|----------------|---------------|
| `search_query` | string          | `""`           | No            |
| `id_list`      | list of strings | `[]`           | No            |
| `start`        | int             | 0              | No            |
| `max_results`  | int             | 10             | No            |
| `sort_by`      | string          | `"relevance"`  | No            |
| `sort_order`   | string          | `"descending"` | No            |

+ `search_query` is a query string; details of its usage are documented [here](https://arxiv.org/help/api/user-manual#Quickstart).
+ `id_list` contains arXiv record IDs (typically of the format `"0710.5765v1"`)
+ `start` is the result offset for paging through a long query result. If set to 0, the API response will begin with the first result; if set to 10, the API response will begin with the 11th.
+ `max_results` is the maximum number of results per query.

All of these arguments are documented more comprehensively in the [arXiv API documentation](https://arxiv.org/help/api/user-manual#Quickstart).

**Query examples:**

```python
import arxiv
# Keyword search
arxiv.query(search_query="quantum")
# Get single record by ID
arxiv.query(id_list=["1707.08567"])
# Get multiple records by ID
arxiv.query(id_list=["1707.08567", "1707.08567"])
```

For a more detailed description of the interaction between `search_query` and `id_list`, see [this section of the arXiv documentation](https://arxiv.org/help/api/user-manual#search_query_and_id_list).

### Download PDF

```python
arxiv.download(obj, dirname, prepend_id, slugify)
```

| **Argument** | **Type** | **Default** | **Required?** |
|--------------|----------|-------------|---------------|
| `obj`        | dict     | N/A         | Yes           |
| `dirname`    | string   | `"./"`      | No            |
| `prepend_id` | boolean  | False       | No            |
| `slugify`    | boolean  | False       | No            |

+ `obj` is a result object, one of a list returned by query(). This function looks up keys `pdf_url` and `title` in `obj` to make the download request.
+ `dirname` is the relative directory path to which the downloaded PDF will be saved. It defaults to the present working directory.
+ When `prepend_id` is True, the arXiv record ID will be prepended to the download filename.
+ When `slugify` is True, the paper title will be stripped of non-alphanumeric characters before being used as a filename.

**Download PDF examples:**

```python
import arxiv
# Query for a paper of interest, then download
paper = arxiv.query(id_list=["1707.08567"])[0]
arxiv.download(paper)
# You can skip the query step if you have the paper info!
paper2 = {"pdf_url": "http://arxiv.org/pdf/1707.08567v1",
          "title": "The Paper Title"}
arxiv.download(paper2)
```
