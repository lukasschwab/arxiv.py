#!/bin/bash
set -e

# Intelligent release script for arxiv.py
# Automatically determines next version based on PyPI and user choice

DRY_RUN="$1"

echo "🚀 Starting release process"

# Ensure we have UV
if ! command -v uv &> /dev/null; then
    echo "❌ UV is required."
    exit 1
fi

# Ensure clean working directory
if [ -n "$(git status --porcelain)" ]; then
    echo "❌ Working directory is not clean. Please commit or stash changes."
    exit 1
fi

echo "✅ Working directory is clean"

# Get current version from PyPI
echo "📡 Fetching current version from PyPI..."
CURRENT_VERSION=$(curl -s https://pypi.org/pypi/arxiv/json | jq -r '.info.version' 2>/dev/null)

if [ "$CURRENT_VERSION" = "0.0.0" ]; then
    echo "⚠️  Could not fetch version from PyPI, using local git tags"
    CURRENT_VERSION=$(git describe --tags --abbrev=0 2>/dev/null | sed 's/^v//' || echo "2.3.2")
fi

echo "📦 Current version on PyPI: $CURRENT_VERSION"

# Parse current version
if [[ $CURRENT_VERSION =~ ^([0-9]+)\.([0-9]+)\.([0-9]+) ]]; then
    MAJOR=${BASH_REMATCH[1]}
    MINOR=${BASH_REMATCH[2]}
    PATCH=${BASH_REMATCH[3]}
else
    echo "❌ Could not parse current version: $CURRENT_VERSION"
    exit 1
fi

# Calculate next versions
NEXT_MAJOR="$((MAJOR + 1)).0.0"
NEXT_MINOR="$MAJOR.$((MINOR + 1)).0"
NEXT_PATCH="$MAJOR.$MINOR.$((PATCH + 1))"

echo ""
echo "📋 Version options:"
echo "  1) Patch:  $CURRENT_VERSION → $NEXT_PATCH (bug fixes)"
echo "  2) Minor:  $CURRENT_VERSION → $NEXT_MINOR (new features, backward compatible)"
echo "  3) Major:  $CURRENT_VERSION → $NEXT_MAJOR (breaking changes)"
echo ""

# Get user choice
if [ "$DRY_RUN" = "--dry-run" ]; then
    VERSION="$NEXT_MINOR"  # Default for dry run
    echo "🔍 DRY RUN: Auto-selecting minor version $VERSION"
else
    read -p "Select version type [1/2/3]: " choice
    case $choice in
        1) VERSION="$NEXT_PATCH" ;;
        2) VERSION="$NEXT_MINOR" ;;
        3) VERSION="$NEXT_MAJOR" ;;
        *) echo "❌ Invalid choice. Exiting."; exit 1 ;;
    esac
fi

echo "🎯 Selected version: $VERSION"
echo ""

# Run tests
echo "🧪 Running tests..."
make check
echo "✅ Tests passed"

# Clean previous builds
echo "🧹 Cleaning previous builds..."
make clean

# Create and push tag
TAG="$VERSION"
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
    echo "🔍 To actually release, run: ./release.sh"
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
echo "   Previous: $CURRENT_VERSION"
echo "   Tag: $TAG" 
echo "   Files in dist/: $(ls -1 dist/ | wc -l)"
echo "   Git commit: $(git rev-parse --short HEAD)"
