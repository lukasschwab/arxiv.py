# arxiv.py

A Python wrapper for the arXiv API.

## Install

```
$ pip install arxiv
```

## Usage

You can use `arxiv.py` as a CLI to navigate arXiv or as a library to query its
API.

### CLI

Currently `arxiv.py` implements three subcommands:
```
$ arxiv download [-t/--timeout seconds] IDS
$ arxiv fetch [-t/--timeout seconds] IDS
$ arxiv find [-i/--ids, -t/--timeout seconds] QUERY
```

The first two commands accept a list of arXiv ids and, respectively, download
the corresponding PDFs or display their metadata in JSON format.

The third command runs a query against arXiv and prints the metadata in JSON
format of the records that match. Adding the `-i/--ids` flag will return only
their ids.

Adding the `-t/--timeout seconds` option will sleep for that amount of seconds
between successive requests to the arXiv API.

Note that the previous commands can be chained, therefore running
```
$ arxiv download $(arxiv find --ids QUERY)
```
will download all papers that match `QUERY`, while
```
$ arxiv fetch $(arxiv find --ids QUERY)
```
will fetch all their metadata.

### API

The previous CLI is built on top of a Python library that can be used on its own
to query arXiv's API. For example:
```python
>>> from arxiv import Client
>>> client = Client()
>>> client.download([IDS])
```
will achieve the same effect as
```
$ arxiv download IDS
```

## Authors

* Lukas Schwab <lukas.schwab@gmail.com>
* Jacopo Notarstefano <jacopo.notarstefano@gmail.com>

## License

MIT
