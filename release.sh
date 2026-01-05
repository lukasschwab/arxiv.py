#!/bin/bash
set -e

# Modern release script for arxiv.py with UV tooling
# Usage: ./release.sh <version> [--dry-run]

VERSION="$1"
DRY_RUN="$2"

if [ -z "$VERSION" ]; then
    echo "Usage: $0 <version> [--dry-run]"
    echo "Example: $0 2.4.0"
    echo "Example: $0 2.4.0 --dry-run"
    exit 1
fi

echo "🚀 Starting release process for version $VERSION"

# Ensure we have UV
if ! command -v uv &> /dev/null; then
    echo "❌ UV is required. Install with: curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

# Ensure clean working directory
if [ -n "$(git status --porcelain)" ]; then
    echo "❌ Working directory is not clean. Please commit or stash changes."
    exit 1
fi

echo "✅ Working directory is clean"

# Run tests
echo "🧪 Running tests..."
make check
echo "✅ Tests passed"

# Clean previous builds
echo "🧹 Cleaning previous builds..."
make clean

# Create and push tag
TAG="v$VERSION"
echo "🏷️  Creating tag $TAG..."

if [ "$DRY_RUN" = "--dry-run" ]; then
    echo "🔍 DRY RUN: Would create tag $TAG"
    echo "🔍 DRY RUN: Would push tag to origin"
else
    git tag -a "$TAG" -m "Release $VERSION"
    git push origin "$TAG"
    echo "✅ Tag $TAG created and pushed"
fi

# Build distributions
echo "📦 Building distributions..."
uv build
echo "✅ Build completed"

# Show what was built
echo "📋 Built distributions:"
ls -la dist/

# Upload to PyPI
if [ "$DRY_RUN" = "--dry-run" ]; then
    echo "🔍 DRY RUN: Would upload to PyPI:"
    echo "   uv publish dist/*"
    echo ""
    echo "🔍 To actually release, run: $0 $VERSION"
else
    echo "📤 Uploading to PyPI..."
    echo "💡 Make sure you have PyPI API token configured"
    echo "💡 Or set: export UV_PUBLISH_TOKEN=pypi-..."
    
    read -p "Continue with PyPI upload? [y/N] " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        uv publish dist/*
        echo "✅ Successfully released $VERSION to PyPI!"
        echo ""
        echo "🎉 Release $VERSION completed successfully!"
        echo "📍 Check: https://pypi.org/project/arxiv/$VERSION/"
    else
        echo "❌ Upload cancelled. You can upload manually later with:"
        echo "   uv publish dist/*"
    fi
fi

echo ""
echo "📝 Release summary:"
echo "   Version: $VERSION"
echo "   Tag: $TAG" 
echo "   Files in dist/: $(ls -1 dist/ | wc -l)"
echo "   Git commit: $(git rev-parse --short HEAD)"
