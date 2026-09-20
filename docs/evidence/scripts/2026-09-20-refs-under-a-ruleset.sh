#!/bin/sh
# Spike: does a repository ruleset that restricts ref creation also refuse
# refs/saffron/*? This is the first of the four things
# docs/evidence/2026-09-17-state-on-git-refs.md left unproven, and the only one
# that changes the design rather than annotating it: DESIGN.md 2.1's
# onboard-any-repo ambition is what it lands on.
#
# THIS CREATES A REAL REMOTE REPOSITORY and does not delete it (the probing
# token has no delete_repo scope). Delete it by hand afterwards:
#   gh auth refresh -h github.com -s delete_repo && gh repo delete <slug> --yes
set -eu
OWNER=${OWNER:-jtmcn}
NAME=${NAME:-saffron-ruleset-spike}
SLUG="$OWNER/$NAME"
REMOTE="git@github.com:$SLUG.git"
ROOT=$(mktemp -d)
export GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_SYSTEM=/dev/null
export GIT_AUTHOR_NAME=s GIT_AUTHOR_EMAIL=s@x
export GIT_COMMITTER_NAME=s GIT_COMMITTER_EMAIL=s@x
say() { printf '\n== %s ==\n' "$1"; }

# A ruleset the probe created is deleted on the way out, so a failure mid-probe
# cannot leave the repository in a state the next run reads as its own result.
RULESET_ID=""
cleanup() {
  [ -n "$RULESET_ID" ] && gh api -X DELETE \
    "repos/$SLUG/rulesets/$RULESET_ID" >/dev/null 2>&1 || true
}
trap cleanup EXIT

say "0. create the throwaway repository"
gh repo create "$SLUG" --private --description "throwaway: saffron ruleset probe" \
  2>&1 | sed 's/^/  /' || echo "  (create failed or repo exists; continuing)"

cd "$ROOT"
git init -q --initial-branch=main src
cd src
echo code > app.py
git add app.py
git commit -qm "the code"
git remote add origin "$REMOTE"
git push -q origin main 2>&1 | tail -2 || echo "  push main FAILED"
echo "  pushed main to $SLUG"

state_commit() {
  # $1 = payload, $2 = optional parent
  _t=$(printf '%s\n' "$1" | git hash-object -w --stdin \
    | xargs -I{} sh -c 'printf "100644 blob {}\tstate\n" | git mktree')
  if [ -n "${2:-}" ]; then
    git commit-tree "$_t" -p "$2" -m "state: $1"
  else
    git commit-tree "$_t" -m "state: $1"
  fi
}

STATE=$(state_commit READY_FOR_REVIEW)
git update-ref refs/saffron/tasks/SA-0099 "$STATE"
echo "  state commit: $STATE"

# Each case installs one ruleset, tries to create refs/saffron/*, then removes
# it. The ref is deleted between cases so every push is a creation, which is
# the operation the "creation" rule names.
try_push() {
  _label=$1
  git push origin ":refs/saffron/tasks/SA-0099" >/dev/null 2>&1 || true
  OUT=$(git push origin \
    "refs/saffron/tasks/SA-0099:refs/saffron/tasks/SA-0099" 2>&1) && RC=0 || RC=$?
  printf '%s\n' "$OUT" | sed 's/^/    /'
  if [ "$RC" -eq 0 ]; then
    echo "    RESULT [$_label]: ACCEPTED"
  else
    echo "    RESULT [$_label]: REFUSED (exit $RC)"
  fi
}

install_ruleset() {
  # $1 = name, $2 = target, $3 = ref_name include JSON, $4 = rules JSON
  RULESET_ID=$(gh api -X POST "repos/$SLUG/rulesets" \
    -f name="$1" -f target="$2" -f enforcement=active \
    --raw-field "conditions={\"ref_name\":{\"include\":$3,\"exclude\":[]}}" \
    --raw-field "rules=$4" \
    --jq '.id' 2>&1) || { echo "    ruleset create FAILED: $RULESET_ID"; RULESET_ID=""; return 1; }
  echo "    ruleset $1 installed (id $RULESET_ID)"
}

remove_ruleset() {
  [ -n "$RULESET_ID" ] || return 0
  gh api -X DELETE "repos/$SLUG/rulesets/$RULESET_ID" >/dev/null 2>&1 || true
  RULESET_ID=""
}

say "1. baseline: no ruleset at all"
gh api "repos/$SLUG/rulesets" --jq 'length' 2>/dev/null \
  | sed 's/^/    rulesets present: /'
try_push "no ruleset"

say "2. branch ruleset, ~ALL, restrict creations"
if install_ruleset "all-refs-no-create" branch '["~ALL"]' \
    '[{"type":"creation"}]'; then
  try_push "branch/~ALL/creation"
fi
remove_ruleset

say "3. branch ruleset, refs/heads/*, restrict creations"
if install_ruleset "heads-no-create" branch '["refs/heads/*"]' \
    '[{"type":"creation"}]'; then
  try_push "branch/refs-heads/creation"
fi
remove_ruleset

say "4. branch ruleset, ~ALL, creation + update + deletion + non-fast-forward"
if install_ruleset "all-refs-locked" branch '["~ALL"]' \
    '[{"type":"creation"},{"type":"update"},{"type":"deletion"},{"type":"non_fast_forward"}]'; then
  try_push "branch/~ALL/locked"
fi
remove_ruleset

say "5. branch ruleset, ~ALL, required pull request"
if install_ruleset "all-refs-need-pr" branch '["~ALL"]' \
    '[{"type":"pull_request","parameters":{"required_approving_review_count":1,"dismiss_stale_reviews_on_push":false,"require_code_owner_review":false,"require_last_push_approval":false,"required_review_thread_resolution":false}}]'; then
  try_push "branch/~ALL/pull_request"
fi
remove_ruleset

say "6. tag ruleset, ~ALL, restrict creations"
if install_ruleset "tags-no-create" tag '["~ALL"]' \
    '[{"type":"creation"}]'; then
  try_push "tag/~ALL/creation"
fi
remove_ruleset

say "7. does the same ruleset actually refuse a BRANCH? (instrument check)"
# If a ~ALL creation rule does not stop a new branch either, the probe is
# measuring a ruleset that never took effect rather than a namespace that
# escapes it.
if install_ruleset "all-refs-no-create-2" branch '["~ALL"]' \
    '[{"type":"creation"}]'; then
  git branch -q probe-branch 2>/dev/null || true
  OUT=$(git push origin probe-branch:probe-branch 2>&1) && RC=0 || RC=$?
  printf '%s\n' "$OUT" | sed 's/^/    /'
  if [ "$RC" -eq 0 ]; then
    echo "    RESULT [branch creation]: ACCEPTED - ruleset is NOT in force"
  else
    echo "    RESULT [branch creation]: REFUSED - ruleset IS in force"
  fi
  git push origin ":probe-branch" >/dev/null 2>&1 || true
fi
remove_ruleset

say "8. final state of the remote"
git ls-remote origin 2>/dev/null | sed 's/^/    /' || echo "    (none)"

echo
echo "root: $ROOT"
echo "delete the repo:  gh auth refresh -h github.com -s delete_repo && gh repo delete $SLUG --yes"
