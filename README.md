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
  + **Note:** multi-field queries must be space-delimited. `au:balents_leon AND cat:cond-mat.str-el` is valid; `au:balents_leon+AND+cat:cond-mat.str-el` is *not* valid.

+ `id_list` contains arXiv record IDs (typically of the format `"0710.5765v1"`)

+ `start` is the result offset for paging through a long query result. If set to 0, the API response will begin with the first result; if set to 10, the API response will begin with the 11th.

+ `max_results` is the maximum number of results per response.

All of these arguments are documented more comprehensively in the [arXiv API documentation](https://arxiv.org/help/api/user-manual#Quickstart).

**Query examples:**

```python
import arxiv
# Keyword queries
arxiv.query(search_query="quantum")
# Multi-field queries
arxiv.query(search_query="au:balents_leon AND cat:cond-mat.str-el")
# Get single record by ID
arxiv.query(id_list=["1707.08567"])
# Get multiple records by ID
arxiv.query(id_list=["1707.08567", "1707.08567"])
```

For a more detailed description of the interaction between `search_query` and `id_list`, see [this section of the arXiv documentation](https://arxiv.org/help/api/user-manual#search_query_and_id_list).

### Download PDF

```python
arxiv.download(obj, dirname, slugify)
```

| **Argument** | **Type** | **Default** | **Required?** |
|--------------|----------|-------------|---------------|
| `obj`        | dict     | N/A         | Yes           |
| `dirname`    | string   | `"./"`      | No            |
| `slugify`    | boolean  | False       | No            |

+ `obj` is a result object, one of a list returned by query(). This function looks up keys `pdf_url` and `title` in `obj` to make the download request.

+ `dirname` is the relative directory path to which the downloaded PDF will be saved. It defaults to the present working directory.

+ `slugify` is a function that processes `obj` into a filename. By default, `arxiv.download(obj)` prepends the object ID to the object title.

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

# Returns the object id
def custom_slugify(obj):
    return obj.get('id').split('/')[-1]

# Download with a specified slugifier function
arxiv.download(paper, slugify=custom_slugify)
```
