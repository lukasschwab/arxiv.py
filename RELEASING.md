# Releasing arxiv

Releases are built and published by `.github/workflows/release.yml` when a
`MAJOR.MINOR.PATCH` tag is pushed. The local script only runs checks and prepares
that tag; it never builds or uploads packages.

## One-time setup (before pushing the first release tag)

1. In GitHub repository **Settings → Environments**, create `pypi`.
   Configure required reviewers where available, so uploading requires approval.
   Allow deployment only from release tags, not branches. Protect release tags
   against unauthorized creation, modification, and deletion with a repository
   ruleset. Restrict workflow changes through normal code review.
2. In PyPI's **arxiv → Manage → Publishing**, add a GitHub Trusted Publisher:

   | Field | Value |
   | --- | --- |
   | Owner | `lukasschwab` |
   | Repository | `arxiv.py` |
   | Workflow filename | `release.yml` |
   | Environment | `pypi` |

   The workflow filename is the basename, not `.github/workflows/release.yml`;
   the environment must match exactly.
3. Merge the workflow and helper changes before using them for a release.
   No PyPI token or GitHub Actions secret is needed. After verifying the first
   successful trusted release, revoke any obsolete publishing API tokens and
   remove copies from local configuration or CI secrets.

## Each release

```sh
git switch master
git pull --ff-only
./release.sh --dry-run
./release.sh
```

Start from a fully committed, clean checkout. The helper reads the current PyPI
version, offers patch/minor/major choices, runs `make check`, and requests
confirmation before pushing an annotated tag. A dry run selects the next minor
version and runs checks without creating a tag, pushing, building, or uploading.

Pushing the tag triggers the release workflow; approving the `pypi` environment
(if reviewers are configured) permits the upload. Monitor the **Release to
PyPI** workflow in GitHub Actions. The script finishing means the tag was
pushed, **not** that PyPI publication succeeded.

The workflow:

- Checks out the exact tagged commit with its Git history.
- Installs dependencies from `uv.lock`, runs the offline checks, and builds with
  the locked build backend. Both distribution versions must match the tag; there
  is no `SETUPTOOLS_SCM_PRETEND_VERSION` override.
- Transfers the wheel and sdist to a separate publishing job. Only that job has
  `id-token: write`; it does not check out or execute the package.
- Uses Trusted Publishing (short-lived OIDC credentials) and the PyPA publishing
  action to generate and upload a PEP 740 publish attestation for **each** file.
  Actions are pinned to commits; update those pins deliberately.

After publication, inspect the release's **Security** tab on PyPI. Both files
should have attestations identifying this repository, workflow, tag, and commit,
and the release should show **Full provenance**. These publish attestations
establish publishing identity and artifact integrity, not code safety,
reproducible builds, or a complete SLSA build-provenance record. GitHub-only
artifact attestations are not a substitute for uploading attestations to PyPI.

## Failures and retries

If building fails, nothing is uploaded. If approval or authentication fails,
correct the environment/Trusted Publisher settings and re-run the failed job
in the original Actions run, preserving its built distributions. Do not move a
published tag or fall back to a local token upload.

If an upload partially succeeds, inspect the files already on PyPI before doing
anything else. The action intentionally does not use `skip-existing`: silently
skipping files can hide a mismatch or missing attestations. Prefer a new patch
release if recovering the exact original artifacts is uncertain.

This setup applies to **new uploads**. It does not backfill attestations onto old
release files. Do not delete/re-upload an existing release to try to add them.

## References

- [PyPI: producing attestations](https://docs.pypi.org/attestations/producing-attestations/)
- [PyPI: adding a Trusted Publisher](https://docs.pypi.org/trusted-publishers/adding-a-publisher/)
- [PyPA publishing action](https://github.com/pypa/gh-action-pypi-publish)
- [PyPI's November 6, 2026 security UI announcement](https://blog.pypi.org/posts/2026-11-06-ui-updates-complete/)
