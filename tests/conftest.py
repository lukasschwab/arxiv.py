"""Fixture infrastructure for offline/online test modes.

By default, tests run against recorded golden-file fixtures (fast,
deterministic). Use ``--live`` to hit the real arXiv API, or ``--record``
to proxy real responses and save them as fixtures for future offline runs.

Fixtures are stored as files under ``tests/fixtures/``, keyed by a
stable hash of the request URL.
"""

import hashlib
import json
import time
import urllib.request
from pathlib import Path
from unittest.mock import patch

import pytest
import requests

FIXTURES_DIR = Path(__file__).parent / "fixtures"

# Track which fixture files are loaded during a run (offline mode only).
_used_fixture_paths: set[Path] = set()


def _url_to_fixture_path(url: str) -> Path:
    """Map a URL to a fixture file path.

    Uses a readable prefix (extracted from query params) plus a short hash
    to keep filenames both human-friendly and collision-free.
    """
    from urllib.parse import parse_qs, urlparse

    parsed = urlparse(url)
    qs = parse_qs(parsed.query)
    parts: list[str] = []
    if qs.get("search_query", [""])[0]:
        parts.append("q_" + qs["search_query"][0])
    if qs.get("id_list", [""])[0]:
        parts.append("id_" + qs["id_list"][0].replace("/", "_").replace(",", "_"))
    parts.append("s" + qs.get("start", ["0"])[0])
    parts.append("m" + qs.get("max_results", ["10"])[0])
    prefix = "_".join(parts)
    url_hash = hashlib.sha256(url.encode()).hexdigest()[:12]
    return FIXTURES_DIR / f"{prefix}_{url_hash}.json"


def _save_fixture(url: str, response: requests.Response) -> None:
    """Persist a response to disk."""
    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)
    path = _url_to_fixture_path(url)
    data = {
        "url": url,
        "status_code": response.status_code,
        # Store body as latin-1 text; XML is always decodable this way and
        # it round-trips through JSON without base64 overhead.
        "body": response.content.decode("latin-1"),
    }
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _load_fixture(url: str) -> requests.Response:
    """Load a previously-recorded response."""
    path = _url_to_fixture_path(url)
    if not path.exists():
        raise FileNotFoundError(
            f"No fixture for URL: {url}\n"
            f"Expected at: {path}\n"
            "Run `pytest --record` to generate fixtures."
        )
    _used_fixture_paths.add(path)
    data = json.loads(path.read_text(encoding="utf-8"))
    resp = requests.Response()
    resp.status_code = data["status_code"]
    resp._content = data["body"].encode("latin-1")
    return resp


# ---------------------------------------------------------------------------
# Pytest hooks & fixtures
# ---------------------------------------------------------------------------


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--live",
        action="store_true",
        default=False,
        help="Run tests against the live arXiv API.",
    )
    parser.addoption(
        "--record",
        action="store_true",
        default=False,
        help="Record live API responses as golden-file fixtures.",
    )


@pytest.fixture(autouse=True)
def _mock_api(request: pytest.FixtureRequest) -> None:  # type: ignore[return]
    """Autouse fixture: patches Session.get and time.sleep unless --live."""
    live = request.config.getoption("--live")
    record = request.config.getoption("--record")

    if live and not record:
        # Run against the real API with no patching.
        yield
        return

    if record:
        # Proxy: call real API, save responses, patch out sleep.
        real_get = requests.Session.get

        def recording_get(self: requests.Session, url: str, **kwargs):  # type: ignore[no-untyped-def]
            resp = real_get(self, url, **kwargs)
            _save_fixture(url, resp)
            return resp

        with (
            patch.object(requests.Session, "get", recording_get),
            patch.object(time, "sleep", lambda _: None),
        ):
            yield
        return

    # Default: offline mode — serve from fixtures, no sleep, stub downloads.
    def fixture_get(self: requests.Session, url: str, **kwargs):  # type: ignore[no-untyped-def]
        return _load_fixture(url)

    def fake_urlretrieve(url: str, filename: str) -> tuple[str, None]:
        """Write a small dummy file so download tests can verify paths."""
        Path(filename).write_bytes(b"FAKE")
        return (filename, None)

    with (
        patch.object(requests.Session, "get", fixture_get),
        patch.object(time, "sleep", lambda _: None),
        patch.object(urllib.request, "urlretrieve", fake_urlretrieve),
    ):
        yield


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    """Fail the run if any fixture files on disk were not used.

    Only checked in offline mode (the default) when the full suite runs.
    Skipped when: --live, --record, -k filter, or specific paths are given.
    """
    if session.config.getoption("--live") or session.config.getoption("--record"):
        return
    if session.config.getoption("keyword"):
        return
    # If specific files/dirs were given (not just the default), skip.
    args = session.config.invocation_params.args
    if args and any(str(a) not in ("", ".") for a in args if not str(a).startswith("-")):
        return

    all_fixtures = set(FIXTURES_DIR.glob("*.json"))
    unused = all_fixtures - _used_fixture_paths
    if unused:
        names = sorted(p.name for p in unused)
        session.exitstatus = pytest.ExitCode.TESTS_FAILED
        tw = session.config.get_terminal_writer()
        tw.sep("=", "UNUSED FIXTURES", red=True)
        tw.line("The following fixture files were not used by any test:")
        for name in names:
            tw.line(f"  {name}")
        tw.line("")
        tw.line("Delete them, or run `pytest --record` to regenerate.")
