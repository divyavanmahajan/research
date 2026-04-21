#!/usr/bin/env bash
set -euo pipefail

# Usage: ./publish.sh [patch|minor|major]
# Bumps the version in pyproject.toml, builds, and uploads to PyPI.
# Requires: hatch, twine (in .venv), node, PYPI_TOKEN env var or ~/.pypirc

BUMP=${1:-patch}

# ── Prerequisites ────────────────────────────────────────────────────────────

require() {
  command -v "$1" &>/dev/null || { echo "ERROR: '$1' not found"; exit 1; }
}

require hatch
require node
require python3.12

TWINE=".venv/bin/twine"
if [[ ! -x "$TWINE" ]]; then
  echo "Installing twine into .venv…"
  .venv/bin/pip install twine -q
fi

# ── Tests ────────────────────────────────────────────────────────────────────

echo "▶ Running backend tests…"
.venv/bin/python -m pytest tests/ -q

echo "▶ Running frontend type-check…"
(cd frontend && npx tsc -b --noEmit 2>&1)

# ── Version bump ─────────────────────────────────────────────────────────────

CURRENT=$(grep '^version' pyproject.toml | head -1 | grep -oE '[0-9]+\.[0-9]+\.[0-9]+')
IFS='.' read -r MAJOR MINOR PATCH <<< "$CURRENT"

case "$BUMP" in
  major) MAJOR=$((MAJOR + 1)); MINOR=0; PATCH=0 ;;
  minor) MINOR=$((MINOR + 1)); PATCH=0 ;;
  patch) PATCH=$((PATCH + 1)) ;;
  *)     echo "ERROR: bump must be patch, minor, or major"; exit 1 ;;
esac

NEW="$MAJOR.$MINOR.$PATCH"
echo "▶ Bumping $CURRENT → $NEW"
sed -i '' "s/^version = \"$CURRENT\"/version = \"$NEW\"/" pyproject.toml

# ── Build ────────────────────────────────────────────────────────────────────

echo "▶ Building wheel + sdist…"
hatch build

# ── Check ────────────────────────────────────────────────────────────────────

echo "▶ Checking packages…"
"$TWINE" check dist/dmv_aptfind-"$NEW"*.whl dist/dmv_aptfind-"$NEW"*.tar.gz

# ── Upload ───────────────────────────────────────────────────────────────────

echo "▶ Uploading to PyPI…"
if [[ -n "${PYPI_TOKEN:-}" ]]; then
  "$TWINE" upload dist/dmv_aptfind-"$NEW"* -u __token__ -p "$PYPI_TOKEN"
else
  "$TWINE" upload dist/dmv_aptfind-"$NEW"*
fi

# ── Git tag ──────────────────────────────────────────────────────────────────

echo "▶ Tagging v$NEW"
git add pyproject.toml
git commit -m "chore: release v$NEW"
git tag "v$NEW"

echo ""
echo "✓ Published dmv-aptfind $NEW"
echo "  https://pypi.org/project/dmv-aptfind/$NEW/"
