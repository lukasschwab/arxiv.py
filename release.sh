#!/bin/bash
set -euo pipefail

# Prepare a tag only. GitHub Actions builds and publishes the tagged commit.
usage() {
    echo "Usage: $0 [--dry-run | --help]"
    echo "Choose a patch, minor, or major release based on the current PyPI version."
    echo "--dry-run selects minor and runs checks, but never creates or pushes a tag."
}

die() {
    echo "Error: $*" >&2
    exit 1
}

DRY_RUN=false
if (( $# > 1 )) || [[ ${1-nonempty} == "" ]]; then
    usage >&2
    exit 1
fi
case "${1:-}" in
    "") ;;
    --dry-run) DRY_RUN=true ;;
    --help|-h) usage; exit 0 ;;
    *) usage >&2; exit 1 ;;
esac

for dependency in git curl jq make uv; do
    command -v "$dependency" >/dev/null 2>&1 || die "$dependency is required."
done

REPO_ROOT=$(git rev-parse --show-toplevel)
cd "$REPO_ROOT"

require_clean_tree() {
    local status
    status=$(git status --porcelain --untracked-files=all) || die "Could not inspect the git tree."
    [[ -z "$status" ]] || die "Working directory is not clean. Commit or stash all changes, including release.sh."
}

require_clean_tree
RELEASE_COMMIT=$(git rev-parse --verify HEAD)

echo "Fetching the current version from PyPI..."
if ! CURRENT_VERSION=$(
    curl --fail --silent --show-error --location https://pypi.org/pypi/arxiv/json |
        jq --exit-status --raw-output '.info.version | select(type == "string")'
); then
    die "Could not fetch a valid version from PyPI; no release will be guessed."
fi

if [[ $CURRENT_VERSION =~ ^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$ ]]; then
    MAJOR=${BASH_REMATCH[1]}
    MINOR=${BASH_REMATCH[2]}
    PATCH=${BASH_REMATCH[3]}
else
    die "Expected a full canonical numeric X.Y.Z version from PyPI, got: $CURRENT_VERSION"
fi

NEXT_MAJOR="$((MAJOR + 1)).0.0"
NEXT_MINOR="$MAJOR.$((MINOR + 1)).0"
NEXT_PATCH="$MAJOR.$MINOR.$((PATCH + 1))"

echo "Current version on PyPI: $CURRENT_VERSION"
echo "Version options:"
echo "  1) Patch: $NEXT_PATCH"
echo "  2) Minor: $NEXT_MINOR"
echo "  3) Major: $NEXT_MAJOR"

if [[ $DRY_RUN == true ]]; then
    VERSION="$NEXT_MINOR"
    echo "DRY RUN: Auto-selecting minor version $VERSION"
else
    read -r -p "Select version type [1/2/3]: " choice || die "Could not read a version choice."
    case "$choice" in
        1) VERSION="$NEXT_PATCH" ;;
        2) VERSION="$NEXT_MINOR" ;;
        3) VERSION="$NEXT_MAJOR" ;;
        *) die "Invalid version choice." ;;
    esac
fi

TAG="$VERSION"
TAG_EXISTS=false
if git show-ref --verify --quiet "refs/tags/$TAG"; then
    TAG_COMMIT=$(git rev-parse --verify "refs/tags/$TAG^{commit}") ||
        die "Tag $TAG does not point to a commit."
    [[ $TAG_COMMIT == "$RELEASE_COMMIT" ]] ||
        die "Tag $TAG already exists at a different commit."
    TAG_EXISTS=true
    echo "Reusing existing tag $TAG at HEAD."
fi

echo "Running checks before pushing any tag..."
make check || die "Checks failed; no tag was created or pushed."
require_clean_tree
[[ $(git rev-parse --verify HEAD) == "$RELEASE_COMMIT" ]] ||
    die "HEAD changed during checks. Start the release again."

echo "GitHub Actions will build commit $RELEASE_COMMIT and publish $VERSION to PyPI."
echo "If this tag is already on origin, a no-op push will NOT start another release."
echo "For an already-pushed tag, rerun its release workflow in GitHub Actions instead."

if [[ $DRY_RUN == true ]]; then
    if [[ $TAG_EXISTS == false ]]; then
        echo "DRY RUN: Would create annotated tag $TAG."
    fi
    echo "DRY RUN: Would push tag $TAG to origin to trigger publishing via GitHub Actions."
    exit 0
fi

printf "Push tag %s and publish to PyPI via GitHub Actions? [y/N] " "$TAG"
if ! read -r REPLY ||
    [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Release cancelled; no tag was created or pushed."
    exit 0
fi

if [[ $TAG_EXISTS == false ]]; then
    git tag -a "$TAG" "$RELEASE_COMMIT" -m "Release $VERSION"
fi
git push origin "refs/tags/$TAG:refs/tags/$TAG"
echo "Tag $TAG is available on origin. Follow the release workflow in GitHub Actions."
