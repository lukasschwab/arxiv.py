"""Exercise release preparation offline, without building or publishing packages."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import textwrap

import pytest


RELEASE_SCRIPT = Path(__file__).resolve().parents[1] / "release.sh"
REAL_GIT = shutil.which("git")
BASH = shutil.which("bash")
pytestmark = pytest.mark.skipif(not REAL_GIT or not BASH, reason="Requires bash and git")


class ReleaseSandbox:
    def __init__(self, root: Path) -> None:
        self.repo = root / "repo"
        self.tools = root / "bin"
        self.log = root / "commands.jsonl"
        self.repo.mkdir()
        self.tools.mkdir()
        self.env = {
            **os.environ,
            "PATH": str(self.tools),
            "RELEASE_LOG": str(self.log),
            "REAL_GIT": str(REAL_GIT),
            "CURL_BODY": json.dumps({"info": {"version": "2.3.4"}}),
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": os.devnull,
        }
        for name in (
            "GIT_DIR",
            "GIT_WORK_TREE",
            "GIT_INDEX_FILE",
            "SETUPTOOLS_SCM_PRETEND_VERSION",
        ):
            self.env.pop(name, None)
        self.git("init", "--quiet")
        self.git("config", "user.name", "Release Test")
        self.git("config", "user.email", "release@example.invalid")
        shutil.copyfile(RELEASE_SCRIPT, self.repo / "release.sh")
        (self.repo / "package.txt").write_text("package contents\n")
        self.git("add", ".")
        self.git("commit", "--quiet", "-m", "Initial commit")
        self._install_tools()

    def git(self, *args: str) -> str:
        return subprocess.check_output(
            [str(REAL_GIT), *args], cwd=self.repo, env=self.env, text=True
        ).strip()

    def _install_tools(self) -> None:
        """Only git's local operations are real; network/build tools are fakes."""
        tool = self.tools / "fake-tool"
        tool.write_text(
            f"#!{sys.executable}\n"
            + textwrap.dedent(
                """\
                import json
                import os
                from pathlib import Path
                import subprocess
                import sys

                name = Path(sys.argv[0]).name
                args = sys.argv[1:]
                with open(os.environ["RELEASE_LOG"], "a") as log:
                    log.write(json.dumps([name, *args]) + "\\n")
                if name == "git":
                    if args[0] == "push":
                        sys.exit(int(os.environ.get("PUSH_EXIT", "0")))
                    os.execv(os.environ["REAL_GIT"], [os.environ["REAL_GIT"], *args])
                elif name == "curl":
                    print(os.environ["CURL_BODY"])
                    sys.exit(int(os.environ.get("CURL_EXIT", "0")))
                elif name == "jq":
                    # Model jq -e's rejection of absent/non-string version values.
                    if os.environ.get("JQ_EXIT"):
                        sys.exit(int(os.environ["JQ_EXIT"]))
                    try:
                        version = json.load(sys.stdin)["info"]["version"]
                        if not isinstance(version, str):
                            sys.exit(1)
                        print(version)
                    except (ValueError, KeyError, TypeError):
                        sys.exit(1)
                elif name == "make":
                    if args != ["check"]:
                        sys.exit("Unexpected make target: " + repr(args))
                    if os.environ.get("MAKE_DIRTY"):
                        with open(os.environ["MAKE_DIRTY"], "a") as changed:
                            changed.write("\\n# changed by checks\\n")
                    if os.environ.get("MAKE_MOVE_HEAD"):
                        subprocess.run(
                            [os.environ["REAL_GIT"], "commit", "--quiet", "--allow-empty",
                             "-m", "Moved during checks"], check=True
                        )
                    sys.exit(int(os.environ.get("MAKE_EXIT", "0")))
                else:
                    sys.exit("Local build or publish attempted: " + name)
                """
            )
        )
        tool.chmod(0o755)
        for name in ("git", "curl", "jq", "make", "uv"):
            (self.tools / name).symlink_to(tool)

    def run(self, *args: str, stdin: str = "") -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [str(BASH), str(self.repo / "release.sh"), *args],
            cwd=self.repo,
            env=self.env,
            input=stdin,
            text=True,
            capture_output=True,
            timeout=15,
        )

    def commands(self) -> list[list[str]]:
        if not self.log.exists():
            return []
        return [json.loads(line) for line in self.log.read_text().splitlines()]

    def assert_no_release(self) -> None:
        assert not self.git("tag", "--list")
        assert not any(command[:2] == ["git", "push"] for command in self.commands())
        assert not any(command[0] == "uv" for command in self.commands())


@pytest.fixture
def release(tmp_path: Path) -> ReleaseSandbox:
    return ReleaseSandbox(tmp_path)


def test_dry_run_checks_but_never_tags_builds_or_publishes(release: ReleaseSandbox) -> None:
    result = release.run("--dry-run")

    assert result.returncode == 0, result.stderr
    assert "Auto-selecting minor version 2.4.0" in result.stdout
    assert "Would create annotated tag 2.4.0" in result.stdout
    assert "Would push tag 2.4.0" in result.stdout
    assert "GitHub Actions" in result.stdout
    commands = release.commands()
    assert ["make", "check"] in commands
    assert all(command[:2] != ["git", "tag"] for command in commands)
    assert all(command[0] != "make" or command == ["make", "check"] for command in commands)
    curl = next(command for command in commands if command[0] == "curl")
    assert "--fail" in curl
    assert curl[-1] == "https://pypi.org/pypi/arxiv/json"
    jq = next(command for command in commands if command[0] == "jq")
    assert "--exit-status" in jq
    assert "--raw-output" in jq
    release.assert_no_release()
    assert not release.git("status", "--porcelain")


@pytest.mark.parametrize(("choice", "version"), [("1", "2.3.5"), ("2", "2.4.0"), ("3", "3.0.0")])
def test_confirmed_release_only_creates_and_pushes_tag(
    release: ReleaseSandbox, choice: str, version: str
) -> None:
    result = release.run(stdin=f"{choice}\ny\n")

    assert result.returncode == 0, result.stderr
    assert release.git("tag", "--list") == version
    assert release.git("cat-file", "-t", f"refs/tags/{version}") == "tag"
    assert release.git("rev-parse", f"{version}^{{commit}}") == release.git("rev-parse", "HEAD")
    commands = release.commands()
    push = ["git", "push", "origin", f"refs/tags/{version}:refs/tags/{version}"]
    assert push in commands
    assert commands.index(["make", "check"]) < commands.index(push)
    assert not any(command[0] == "uv" for command in commands)
    assert f"Push tag {version} and publish to PyPI via GitHub Actions? [y/N]" in result.stdout


@pytest.mark.parametrize("confirmation", ["", "\n", "n\n", "yes\n"])
def test_declining_or_missing_confirmation_leaves_no_tag(
    release: ReleaseSandbox, confirmation: str
) -> None:
    result = release.run(stdin="1\n" + confirmation)

    assert result.returncode == 0
    assert "cancelled" in result.stdout
    assert ["make", "check"] in release.commands()
    release.assert_no_release()


@pytest.mark.parametrize("args", [[""], ["--unknown"], ["1.2.3"], ["--dry-run", "extra"]])
def test_invalid_arguments_fail_before_doing_work(release: ReleaseSandbox, args: list[str]) -> None:
    result = release.run(*args)

    assert result.returncode != 0
    assert "Usage:" in result.stderr
    assert not release.commands()
    release.assert_no_release()


@pytest.mark.parametrize("args", [["--help"], ["-h"]])
def test_help_does_not_run_checks(release: ReleaseSandbox, args: list[str]) -> None:
    result = release.run(*args)

    assert result.returncode == 0
    assert "--dry-run" in result.stdout
    assert not release.commands()


@pytest.mark.parametrize("dependency", ["git", "curl", "jq", "make", "uv"])
def test_missing_dependencies_fail_early(release: ReleaseSandbox, dependency: str) -> None:
    (release.tools / dependency).unlink()

    result = release.run("--dry-run")

    assert result.returncode != 0
    assert f"{dependency} is required" in result.stderr
    assert not release.commands()
    release.assert_no_release()


@pytest.mark.parametrize("path", ["release.sh", "package.txt", "untracked.txt"])
@pytest.mark.parametrize("staged", [False, True])
def test_dirty_tree_including_script_is_rejected(
    release: ReleaseSandbox, path: str, staged: bool
) -> None:
    with (release.repo / path).open("a") as changed:
        changed.write("\n# uncommitted change\n")
    if staged:
        release.git("add", path)

    result = release.run("--dry-run")

    assert result.returncode != 0
    assert "not clean" in result.stderr
    assert not any(command[0] in ("curl", "make") for command in release.commands())
    release.assert_no_release()


@pytest.mark.parametrize(
    "env",
    [
        {"CURL_EXIT": "22"},
        {"JQ_EXIT": "4"},
        {"CURL_BODY": "not JSON"},
        {"CURL_BODY": "{}"},
        {"CURL_BODY": '{"info": {"version": null}}'},
        {"CURL_BODY": '{"info": {"version": 234}}'},
    ],
)
def test_fetch_failures_do_not_guess_a_version(
    release: ReleaseSandbox, env: dict[str, str]
) -> None:
    release.env.update(env)

    result = release.run("--dry-run")

    assert result.returncode != 0
    assert "Could not fetch a valid version" in result.stderr
    assert ["make", "check"] not in release.commands()
    assert not any(command[:2] == ["git", "describe"] for command in release.commands())
    release.assert_no_release()


@pytest.mark.parametrize(
    "version",
    [
        "",
        "null",
        "v2.3.4",
        "2.3",
        "2.3.4rc1",
        "2.3.4.post1",
        "2.3.4.5",
        "2.3.4\njunk",
        "02.3.4",
        "2.03.4",
        "2.3.04",
    ],
)
def test_only_full_canonical_numeric_versions_are_accepted(
    release: ReleaseSandbox, version: str
) -> None:
    release.env["CURL_BODY"] = json.dumps({"info": {"version": version}})

    result = release.run("--dry-run")

    assert result.returncode != 0
    assert "full canonical numeric X.Y.Z" in result.stderr
    assert ["make", "check"] not in release.commands()
    release.assert_no_release()


def test_zero_version_is_not_a_fallback_sentinel(release: ReleaseSandbox) -> None:
    release.env["CURL_BODY"] = json.dumps({"info": {"version": "0.0.0"}})

    result = release.run("--dry-run")

    assert result.returncode == 0, result.stderr
    assert "Auto-selecting minor version 0.1.0" in result.stdout
    release.assert_no_release()


@pytest.mark.parametrize("choice", ["", "0\n", "4\n", "patch\n"])
def test_invalid_or_missing_version_choice_never_releases(
    release: ReleaseSandbox, choice: str
) -> None:
    result = release.run(stdin=choice)

    assert result.returncode != 0
    assert ["make", "check"] not in release.commands()
    release.assert_no_release()


def test_failed_checks_do_not_tag_or_push(release: ReleaseSandbox) -> None:
    release.env["MAKE_EXIT"] = "2"

    result = release.run(stdin="1\ny\n")

    assert result.returncode != 0
    assert "Checks failed" in result.stderr
    release.assert_no_release()


def test_checks_cannot_leave_a_dirty_tree(release: ReleaseSandbox) -> None:
    release.env["MAKE_DIRTY"] = "release.sh"

    result = release.run(stdin="1\ny\n")

    assert result.returncode != 0
    assert "not clean" in result.stderr
    release.assert_no_release()


def test_checks_cannot_move_head(release: ReleaseSandbox) -> None:
    release.env["MAKE_MOVE_HEAD"] = "1"

    result = release.run(stdin="1\ny\n")

    assert result.returncode != 0
    assert "HEAD changed" in result.stderr
    release.assert_no_release()


@pytest.mark.parametrize("annotated", [False, True])
def test_existing_tag_at_head_can_be_reused(release: ReleaseSandbox, annotated: bool) -> None:
    if annotated:
        release.git("tag", "-a", "2.3.5", "-m", "Existing release")
    else:
        release.git("tag", "2.3.5")
    original_tag = release.git("rev-parse", "refs/tags/2.3.5")

    result = release.run(stdin="1\ny\n")

    assert result.returncode == 0, result.stderr
    assert release.git("rev-parse", "refs/tags/2.3.5") == original_tag
    assert "Reusing existing tag" in result.stdout
    assert "rerun its release workflow in GitHub Actions" in result.stdout
    assert ["git", "push", "origin", "refs/tags/2.3.5:refs/tags/2.3.5"] in release.commands()
    assert not any(command[:2] == ["git", "tag"] for command in release.commands())


def test_existing_tag_at_another_commit_is_rejected(release: ReleaseSandbox) -> None:
    release.git("tag", "2.3.5")
    release.git("commit", "--quiet", "--allow-empty", "-m", "New commit")

    result = release.run(stdin="1\ny\n")

    assert result.returncode != 0
    assert "different commit" in result.stderr
    assert ["make", "check"] not in release.commands()
    assert not any(command[:2] == ["git", "push"] for command in release.commands())


def test_failed_push_is_not_reported_as_success(release: ReleaseSandbox) -> None:
    release.env["PUSH_EXIT"] = "1"

    result = release.run(stdin="1\ny\n")

    assert result.returncode != 0
    assert "available on origin" not in result.stdout
    assert release.git("tag", "--list") == "2.3.5"
    assert not any(command[0] == "uv" for command in release.commands())
