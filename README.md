# arxiv.py
[![PyPI](https://img.shields.io/pypi/v/arxiv)](https://pypi.org/project/arxiv/) ![PyPI - Python Version](https://img.shields.io/pypi/pyversions/arxiv) [![GitHub Workflow Status (branch)](https://img.shields.io/github/actions/workflow/status/lukasschwab/arxiv.py/python-test.yml?branch=master)](https://github.com/lukasschwab/arxiv.py/actions?query=branch%3Amaster) [![Full package documentation](https://img.shields.io/badge/docs-hosted-brightgreen)](https://lukasschwab.me/arxiv.py/index.html)

Python wrapper for [the arXiv API](https://arxiv.org/help/api/index).

[arXiv](https://arxiv.org/) is a project by the Cornell University Library that provides open access to 1,000,000+ articles in Physics, Mathematics, Computer Science, Quantitative Biology, Quantitative Finance, and Statistics.

## Usage

Install the package:

```bash
$ pip install arxiv   # Or `uv add arxiv` or similar.
```

In your Python code, include the line:

```python
import arxiv
```

### Examples

#### Fetching results

```python
import arxiv

# Construct the default API client.
client = arxiv.Client()

# Search for the 10 most recent articles matching the keyword "quantum."
search = arxiv.Search(
  query = "quantum",
  max_results = 10,
  sort_by = arxiv.SortCriterion.SubmittedDate
)

results = client.results(search)

# `results` is a generator; you can iterate over its elements one by one...
for r in client.results(search):
  print(r.title)
# ...or exhaust it into a list. Careful: this is slow for large results sets.
all_results = list(results)
print([r.title for r in all_results])

# For advanced query syntax documentation, see the arXiv API User Manual:
# https://arxiv.org/help/api/user-manual#query_details
search = arxiv.Search(query = "au:del_maestro AND ti:checkerboard")
first_result = next(client.results(search))
print(first_result)

# Search for the paper with ID "1605.08386v1"
search_by_id = arxiv.Search(id_list=["1605.08386v1"])
# Reuse client to fetch the paper, then print its title.
first_result = next(client.results(search_by_id))
print(first_result.title)
```

> [!TIP]
> [`arxivql`](https://pypi.org/project/arxivql/) may simplify constructing complex query strings.

#### Fetching results with a custom client

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

#### Downloading a paper

```python
import arxiv
from urllib.request import urlretrieve

paper = next(arxiv.Client().results(arxiv.Search(id_list=["1605.08386v1"])))

# Download the PDF.
urlretrieve(paper.pdf_url, "paper.pdf")

# Download the source tarball.
urlretrieve(paper.source_url(), "paper.tar.gz")
```

#### Logging

To inspect this package's network behavior and API logic, configure a `DEBUG`-level logger.

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

## Types 

### Client

A `Client` specifies a reusable strategy for fetching results from arXiv's API. For most use cases the default client should suffice.

Clients configurations specify pagination and retry logic. *Reusing* a client allows successive API calls to use the same connection pool and ensures they abide by the rate limit you set.

### Search

A `Search` specifies a search of arXiv's database. Use `Client.results` to get a generator yielding `Result`s.

### Result

The `Result` objects yielded by `Client.results` include metadata about each paper.

The meaning of the underlying raw data is documented in the [arXiv API User Manual: Details of Atom Results Returned](https://arxiv.org/help/api/user-manual#_details_of_atom_results_returned).

## Development

This project uses [UV](https://astral.sh/uv) for development, while maintaining compatibility with traditional pip installation for end users.

Run these commands from a checkout. They use the committed `uv.lock`; `--locked`
fails rather than silently updating an out-of-date lockfile.

| Environment | Install | Run |
| --- | --- | --- |
| Runtime only | `make install` | `uv run --no-sync python` |
| Default development (tests, lint, types) | `make install-dev` | `make check` |
| Tests only | `uv sync --locked --no-default-groups --group test` | `uv run --no-sync pytest` |
| Lint/type tools only | `uv sync --locked --no-default-groups --group lint` | `uv run --no-sync ruff check .`, `uv run --no-sync ruff format --check .`, `uv run --no-sync mypy arxiv` |
| Documentation only | `uv sync --locked --no-default-groups --group docs` | `uv run --no-sync pdoc --docformat restructuredtext ./arxiv/__init__.py '!arxiv._feed' -o docs` |
| Security audit | `make audit` installs the opt-in audit tools and audits the lockfile | See below |

The default `dev` group includes `test` and `lint`; documentation and audit tools
are opt-in, not runtime dependencies. Use `uv sync --locked --all-groups` only
when you want every tool installed. Syncing is exact, so changing groups removes
unneeded packages. After a scoped sync, use `uv run --no-sync` to preserve that
environment: plain `uv run` would install the default development group again.
The standalone `make test`, `make lint`, `make type-check`, `make format`, and
`make docs` targets explicitly select their own groups and enforce the lockfile.
`make clean` removes project artifacts, not the shared uv cache.

The local interpreter defaults to `.python-version`. To select another supported
version consistently for both sync and run, set `UV_PYTHON`, for example
`UV_PYTHON=3.13 make test`. CI selects and verifies each test interpreter
explicitly, rather than merely installing it. Add `--live` to the pytest command
to exercise the real arXiv API instead of offline fixtures.

`make audit` exports **all groups** from the committed lockfile with hashes and
audits those pinned requirements using stable `pip-audit`, without re-resolving
dependencies or auditing only the scanner's installed environment. This includes
test, lint/type, docs, scanner, and build-backend dependencies; the audit group
mirrors `build-system.requires` to keep the build tools in the lockfile too.
The audit checks known vulnerabilities by package/version, not artifact contents.
Requirement markers are evaluated for the current interpreter/platform; CI
audits each supported Python version on Linux, on PRs and weekly for newly
disclosed vulnerabilities. This does not check platform-only dependencies for
other operating systems. To audit those, run `make audit` on that platform.

After `make audit`, `uv run --no-sync uv build --no-build-isolation --wheel` builds with those
same locked, audited backend versions (also checked in CI). Normal isolated
PEP 517 builds, including end-user pip installations, resolve their build tools
independently of `uv.lock`.

When intentionally changing dependencies, update `pyproject.toml` and run
`uv lock`, review the lockfile diff, then run the relevant checks above.
Ordinary installation and CI should not regenerate the lockfile.

