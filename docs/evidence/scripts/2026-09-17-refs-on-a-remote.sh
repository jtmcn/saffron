#!/bin/sh
# Spike: does GitHub accept, store and serve back state on refs/saffron/*?
#
# THIS WRITES TO A REAL REMOTE. It pushes refs/saffron/tasks/SA-0099 to $REMOTE
# and does NOT delete it, so point it at a throwaway repo you can discard.
# The companion probe, 2026-09-17-refs-a-cell-can-reach.sh, is fully local.
set -eu
REMOTE="git@github.com:jtmcn/saffron-ref-spike.git"
SLUG="jtmcn/saffron-ref-spike"
ROOT=$(mktemp -d)
cd "$ROOT"
export GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_SYSTEM=/dev/null
export GIT_AUTHOR_NAME=s GIT_AUTHOR_EMAIL=s@x
export GIT_COMMITTER_NAME=s GIT_COMMITTER_EMAIL=s@x
say() { printf '\n== %s ==\n' "$1"; }

git init -q --initial-branch=main src
cd src
echo code > app.py
git add app.py
git commit -qm "the code"
git remote add origin "$REMOTE"
git push -q origin main 2>&1 | tail -2 || echo "  push main FAILED"

# orphan state commit on a non-branch ref
TREE=$(printf 'READY_FOR_REVIEW\n' | git hash-object -w --stdin \
  | xargs -I{} sh -c 'printf "100644 blob {}\tstate\n" | git mktree')
STATE=$(git commit-tree "$TREE" -m "task SA-0099 -> READY_FOR_REVIEW")
git update-ref refs/saffron/tasks/SA-0099 "$STATE"
echo "state commit: $STATE"

say "1. push refs/saffron/tasks/SA-0099"
if git push origin "refs/saffron/tasks/SA-0099:refs/saffron/tasks/SA-0099" 2>&1 | sed 's/^/  /'; then
  echo "  RESULT: accepted"
else
  echo "  RESULT: REFUSED"
fi

say "2. git ls-remote sees it?"
git ls-remote origin 'refs/saffron/*' | sed 's/^/  /' || echo "  (none)"

say "3. GitHub API: is it listed under git/refs?"
gh api "repos/$SLUG/git/refs" --jq '.[].ref' 2>/dev/null | sed 's/^/  /' \
  || echo "  (git/refs listing returned nothing or errored)"

say "4. GitHub API: is it listed as a BRANCH?"
gh api "repos/$SLUG/branches" --jq '.[].name' 2>/dev/null | sed 's/^/  /'

say "5. gh pr list unaffected?"
gh pr list --repo "$SLUG" 2>&1 | head -3 | sed 's/^/  /'

say "6. fresh clone: does a default clone bring the ref or its object?"
cd "$ROOT"
git clone -q "$REMOTE" fresh
cd fresh
git for-each-ref --format='  %(refname)' | head
if git rev-parse --verify -q refs/saffron/tasks/SA-0099 >/dev/null; then
  echo "  ref PRESENT after default clone"
else
  echo "  ok: ref absent after default clone"
fi
if git cat-file -e "$STATE" 2>/dev/null; then
  echo "  object PRESENT after default clone"
else
  echo "  ok: object absent after default clone"
fi

say "7. can it be fetched back explicitly?"
git fetch -q origin 'refs/saffron/*:refs/saffron/*' 2>&1 | sed 's/^/  /' || echo "  fetch FAILED"
if git rev-parse --verify -q refs/saffron/tasks/SA-0099 >/dev/null; then
  echo "  ok: round-tripped, ref = $(git rev-parse refs/saffron/tasks/SA-0099)"
  echo "  content: $(git cat-file -p refs/saffron/tasks/SA-0099:state 2>/dev/null | tr -d '\n')"
else
  echo "  FAILED: could not fetch it back"
fi

say "8. does a second push to the same ref update it (CAS shape)?"
cd "$ROOT/src"
TREE2=$(printf 'MERGED\n' | git hash-object -w --stdin \
  | xargs -I{} sh -c 'printf "100644 blob {}\tstate\n" | git mktree')
STATE2=$(git commit-tree "$TREE2" -p "$STATE" -m "task SA-0099 -> MERGED")
git update-ref refs/saffron/tasks/SA-0099 "$STATE2"
git push origin "refs/saffron/tasks/SA-0099:refs/saffron/tasks/SA-0099" 2>&1 | sed 's/^/  /'
echo "  remote now: $(git ls-remote origin refs/saffron/tasks/SA-0099 | cut -f1)"
echo "  expected:   $STATE2"

say "9. does a stale (non-fast-forward) push get refused without --force?"
STATE3=$(git commit-tree "$TREE" -m "divergent")
git update-ref refs/saffron/tasks/SA-0099 "$STATE3"
# git's status, not sed's: the first version of this probe put the push in a
# pipeline and read the pipeline's status, so it reported a rejection as
# "accepted". Capture the output, then test the exit code directly.
OUT=$(git push origin "refs/saffron/tasks/SA-0099:refs/saffron/tasks/SA-0099" 2>&1) && RC=0 || RC=$?
printf '%s\n' "$OUT" | sed 's/^/  /'
if [ "$RC" -eq 0 ]; then
  echo "  RESULT: accepted (no fast-forward protection on this namespace)"
else
  echo "  RESULT: refused (exit $RC) - non-fast-forward protection applies"
fi

echo
echo "root: $ROOT"
