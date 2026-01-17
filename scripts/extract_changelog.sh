#!/bin/bash
# Extract changelog section for a specific version from CHANGELOG.md
#
# Usage: ./extract_changelog.sh <version> [changelog_file]
# Example: ./extract_changelog.sh v1.3.0
#          ./extract_changelog.sh v1.3.0 ./CHANGELOG.md
#
# Output: Prints the changelog section to stdout, saves to VERSION_changelog.txt

set -euo pipefail

VERSION="${1:-}"
CHANGELOG_FILE="${2:-CHANGELOG.md}"

if [ -z "$VERSION" ]; then
    echo "Error: Version argument required" >&2
    echo "Usage: $0 <version> [changelog_file]" >&2
    exit 1
fi

if [ ! -f "$CHANGELOG_FILE" ]; then
    echo "Error: Changelog file not found: $CHANGELOG_FILE" >&2
    exit 1
fi

# Strip 'v' prefix if present to match CHANGELOG format
CLEAN_VERSION="${VERSION#v}"

# Extract the section for this version
# Matches from "## 📦 Release <VERSION>" until the next "## 📦 Release" or end of file
changelog=$(awk -v target="$CLEAN_VERSION" '
    /^## 📦 Release / {
        # Check if this line is the start of our target version
        if ($0 ~ target) {
            flag=1
            print
            next
        } else {
            # Start of another release, stop printing
            flag=0
        }
    }
    flag { print }
' "$CHANGELOG_FILE")

# Fallback: If extraction returns empty, try strict match failure handling
if [ -z "$changelog" ]; then
    echo "Warning: Could not extract specific changelog for $VERSION (tried $CLEAN_VERSION)" >&2
    # Fallback to just the top lines if desperate
    changelog=$(head -n 50 "$CHANGELOG_FILE")
fi

# Output to stdout
echo "$changelog"
