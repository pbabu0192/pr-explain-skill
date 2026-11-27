#!/bin/sh
# Copies the pr-explain files, unchanged, from the latest t2pr release (or the tag given).
# usage: ./sync.sh [tag]     needs gh with read access to the t2pr repo
set -eu

src=${T2PR_REPO:-pbabu0192/t2pr}
cd "$(dirname -- "$0")"
tag=${1:-$(gh release view -R "$src" --json tagName -q .tagName)}

get() { # get <t2pr path> <local path>
  mkdir -p "$(dirname -- "$2")"
  gh api -H 'Accept: application/vnd.github.raw' "repos/$src/contents/$1?ref=$tag" > "$2.new"
  mv "$2.new" "$2"
}
get .github/skills/pr-explain/SKILL.md GUIDE.md
get .github/skills/pr-explain/BUILDER.md BUILDER.md
get scripts/pr-visual.py scripts/pr-visual.py
get scripts/pr-page.css scripts/pr-page.css
get scripts/pr-page.js scripts/pr-page.js
get templates/learning.md templates/learning.md
chmod +x scripts/pr-visual.py

# SKILL.md overrides these parts by name. If one is gone, update SKILL.md before you share.
failed=0
need() { grep -Fq -- "$2" "$1" || { echo "anchor gone in $1: $2" >&2; failed=1; }; }
need GUIDE.md '## Page'
need GUIDE.md 'pr-page.sh start'
need GUIDE.md '`<workbench>/scripts/pr-visual.py'
need GUIDE.md '<workbench>/templates/learning.md'
need GUIDE.md 'Write `context.md` beside it'
need BUILDER.md '## Start'
need BUILDER.md '## Answer loop'
need BUILDER.md 'Open `explain.html` with lavish'
need scripts/pr-visual.py 'mode == "b"'
[ "$failed" -eq 0 ] || exit 1

echo "$tag" > T2PR_VERSION
echo "Synced t2pr $tag. Check: git diff --stat; then commit and push."
