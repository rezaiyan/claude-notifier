#!/usr/bin/env bash
# Usage: ./scripts/bump-version.sh [major|minor|patch|x.y.z]
#
# - Updates VERSION
# - Moves [Unreleased] in CHANGELOG.md to the new version
# - Commits, tags, and pushes
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

BOLD='\033[1m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
info()  { echo -e "${GREEN}▶${NC} $*"; }
warn()  { echo -e "${YELLOW}⚠${NC}  $*"; }
error() { echo -e "${RED}✖${NC}  $*" >&2; exit 1; }

# ── Validate working tree ─────────────────────────────────────────────────────
if [[ -n "$(git status --porcelain)" ]]; then
  error "Working tree is not clean. Commit or stash changes before bumping."
fi

# ── Parse current version ─────────────────────────────────────────────────────
current=$(tr -d '[:space:]' < VERSION)
major=$(echo "$current" | cut -d. -f1)
minor=$(echo "$current" | cut -d. -f2)
patch=$(echo "$current" | cut -d. -f3)

# ── Calculate new version ─────────────────────────────────────────────────────
arg="${1:-patch}"

if [[ "$arg" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
  new="$arg"
elif [[ "$arg" == "major" ]]; then
  new="$((major + 1)).0.0"
elif [[ "$arg" == "minor" ]]; then
  new="${major}.$((minor + 1)).0"
elif [[ "$arg" == "patch" ]]; then
  new="${major}.${minor}.$((patch + 1))"
else
  error "Usage: bump-version.sh [major|minor|patch|x.y.z]"
fi

today=$(date +%Y-%m-%d)
info "Bumping ${BOLD}${current}${NC} → ${BOLD}${new}${NC}"

# ── Check CHANGELOG has an [Unreleased] section ───────────────────────────────
if ! grep -q "## \[Unreleased\]" CHANGELOG.md; then
  error "No [Unreleased] section found in CHANGELOG.md. Add your changes there first."
fi

# ── Update VERSION ────────────────────────────────────────────────────────────
echo "$new" > VERSION
info "Updated VERSION"

# ── Update CHANGELOG.md ───────────────────────────────────────────────────────
python3 - "$new" "$today" <<'PYEOF'
import sys, pathlib

version, date = sys.argv[1], sys.argv[2]
path = pathlib.Path("CHANGELOG.md")
content = path.read_text()

replacement = f"## [Unreleased]\n\n## [{version}] - {date}"
content = content.replace("## [Unreleased]", replacement, 1)
path.write_text(content)
PYEOF
info "Updated CHANGELOG.md"

# ── Commit, tag, push ─────────────────────────────────────────────────────────
git add VERSION CHANGELOG.md
git commit -m "chore: release v${new}"
git tag "v${new}"
git push
git push origin "v${new}"
info "Pushed commit and tag ${BOLD}v${new}${NC}"

# ── Post-release instructions ─────────────────────────────────────────────────
tarball_url="https://github.com/rezaiyan/claude-notifier/archive/refs/tags/v${new}.tar.gz"

echo
echo -e "${BOLD}  Next steps for Homebrew formula:${NC}"
echo
echo -e "  1. Wait ~30 s for GitHub to create the release tarball, then:"
echo -e "     ${YELLOW}curl -sL ${tarball_url} | shasum -a 256${NC}"
echo
echo -e "  2. Update ${BOLD}Formula/claude-notifier.rb${NC}:"
echo -e "     url \"${tarball_url}\""
echo -e "     sha256 \"<paste here>\""
echo
echo -e "  3. Commit to your homebrew-tap repo."
echo
