#!/usr/bin/env bash
# One-time GitHub setup for the repo: topics, labels, Discussions, and the good first issues.
# Needs the GitHub CLI logged in as the repo owner:  gh auth login
#
#   bash scripts/github-setup.sh            # does everything
#   bash scripts/github-setup.sh --dry-run  # just prints what it would do
set -euo pipefail

REPO="byshivam/arya-bank-sandbox"
DRY=${1:-}
run() { if [ "$DRY" = "--dry-run" ]; then echo "+ $*"; else "$@"; fi; }

echo "== description, homepage, topics, Discussions"
run gh repo edit "$REPO" \
  --description "Free practice sandbox for QA engineers: a fake bank (payments API + net banking UI) with 16 planted bugs. One Docker command, then find them." \
  --enable-discussions \
  --add-topic api-testing --add-topic test-automation --add-topic practice --add-topic qa \
  --add-topic fastapi --add-topic playwright --add-topic banking --add-topic software-testing \
  --add-topic testing-tools --add-topic accessibility-testing

echo "== labels"
label() { run gh label create "$1" --repo "$REPO" --color "$2" --description "$3" --force; }
label "good first issue" 7057ff "Small, well-described, good for a first PR"
label "help wanted"      008672 "Extra hands welcome"
label "challenge idea"   fbca04 "A new planted bug or challenge"
label "starter-suite"    0e8a16 "Example test suites for learners"
label "payments-api"     1d76db "services/payments-api"
label "netbanking-web"   5319e7 "services/netbanking-web"
label "docs"             0075ca "Documentation"

echo "== good first issues"
for f in "$(dirname "$0")"/good-first-issues/*.md; do
  title=$(sed -n 's/^title: //p' "$f" | head -1)
  labels=$(sed -n 's/^labels: //p' "$f" | head -1)
  body=$(awk 'f{print} /^---$/{f=1}' "$f")
  if gh issue list --repo "$REPO" --state all --search "in:title \"$title\"" --json title -q '.[].title' | grep -qxF "$title"; then
    echo "skip (exists): $title"; continue
  fi
  args=(--repo "$REPO" --title "$title" --body "$body")
  IFS=',' read -ra ls <<< "$labels"
  for l in "${ls[@]}"; do args+=(--label "$(echo "$l" | xargs)"); done
  run gh issue create "${args[@]}"
done

echo "Done. Two things the CLI can't do for you:"
echo "  1. Make the Docker image public: github.com/users/byshivam/packages/container/arya-bank-sandbox/settings -> Change visibility -> Public"
echo "  2. Install the all-contributors app: https://allcontributors.org/docs/en/bot/installation"
