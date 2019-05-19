# arxiv.py [![Python 2.7](https://img.shields.io/badge/python-2.7-blue.svg)](https://www.python.org/downloads/release/python-270/) [![Python 3.6](https://img.shields.io/badge/python-3.7-blue.svg)](https://www.python.org/downloads/release/python-370/)

Python wrapper for [the arXiv API](http://arxiv.org/help/api/index).

## About arXiv

[arXiv](http://arxiv.org/) is a project by the Cornell University Library that provides open access to 1,000,000+ articles in Physics, Mathematics, Computer Science, Quantitative Biology, Quantitative Finance, and Statistics.

## Usage

### Installation

```bash
$ pip install arxiv
```

Verify the installation with

```bash
$ python setup.py test
```

In your Python script, include the line

```python
import arxiv
```

### Query

```python
arxiv.query(search_query="",
            id_list=[],
            max_results=None,
            sort_by="relevance",
            sort_order="descending",
            prune=True,
            iterative=False,
            max_chunk_results=1000)
```

| **Argument**   | **Type**        | **Default**    |
|----------------|-----------------|----------------|
| `search_query` | string          | `""`           |
| `id_list`      | list of strings | `[]`           |
| `max_results`  | int             | 10             |
| `sort_by`      | string          | `"relevance"`  |
| `sort_order`   | string          | `"descending"` |
| `prune`        | boolean         | `True`         |
| `iterative`    | boolean         | `False`        |
| `max_chunk_results` | int        | 1000           |

+ `search_query`: an arXiv query string. Format documented [here](https://arxiv.org/help/api/user-manual#Quickstart).
  + **Note:** multi-field queries must be space-delimited. `au:balents_leon AND cat:cond-mat.str-el` is valid; `au:balents_leon+AND+cat:cond-mat.str-el` is *not* valid.

+ `id_list`: list of arXiv record IDs (typically of the format `"0710.5765v1"`).

+ `max_results`: the maximum number of results returned by the query.

+ `sort_by`: the arXiv field by which the result should be sorted.

+ `sort_order`: the sorting order, i.e. "ascending", "descending" or None.

+ `prune`: when `True`, received abstract objects will be simplified.

+ `iterative`: when `True`, `query()` will return an iterator. Otherwise, `query()` iterates internally and returns the full list of results.

+ `max_chunk_results`: the maximum number of abstracts ot be retrieved by a single internal request to the arXiv API.

**Query examples:**

```python
import arxiv

# Keyword queries
arxiv.query(search_query="quantum", max_results=100)
# Multi-field queries
arxiv.query(search_query="au:balents_leon AND cat:cond-mat.str-el")
# Get single record by ID
arxiv.query(id_list=["1707.08567"])
# Get multiple records by ID
arxiv.query(id_list=["1707.08567", "1707.08567"])

# Get interator over query results
result = arxiv.query(search_query="quantum", max_chunk_results=10, iterative=True)
for paper in result():
   print(paper)
```

For a more detailed description of the interaction between `search_query` and `id_list`, see [this section of the arXiv documentation](https://arxiv.org/help/api/user-manual#search_query_and_id_list).

### Download article PDF

```python
arxiv.download(obj, dirpath="./", slugify=arxiv.slugify)
```

| **Argument** | **Type** | **Default** | **Required?** |
|--------------|----------|-------------|---------------|
| `obj`        | dict     | N/A         | Yes           |
| `dirpath`    | string   | `"./"`      | No            |
| `slugify`    | function | `arxiv.slugify` | No        |

+ `obj` is a result object, one of a list returned by query(). `obj` must at minimum contain values corresponding to `pdf_url` and `title`.

+ `dirpath` is the relative directory path to which the downloaded PDF will be saved. It defaults to the present working directory.

+ `slugify` is a function that processes `obj` into a filename. By default, `arxiv.download(obj)` prepends the object ID to the object title.

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

## Contributors

<a href="https://github.com/lukasschwab/arxiv.py/graphs/contributors">
  <img src="https://contributors-img.firebaseapp.com/image?repo=lukasschwab/arxiv.py" />
</a>
