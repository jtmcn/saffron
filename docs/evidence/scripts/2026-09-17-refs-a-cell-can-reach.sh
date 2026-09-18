#!/bin/sh
# Spike: can a cell see state kept on refs/saffron/* in the mirror it clones from?
# Reproduces saffron/cell/worktree.py's exact seed sequence.
set -eu
ROOT=$(mktemp -d)
cd "$ROOT"
export GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_SYSTEM=/dev/null
export GIT_AUTHOR_NAME=s GIT_AUTHOR_EMAIL=s@x
export GIT_COMMITTER_NAME=s GIT_COMMITTER_EMAIL=s@x

echo "root: $ROOT"

# --- the target repo, as it would be on the remote -------------------------
git init -q --initial-branch=main origin.git-src
cd origin.git-src
echo "code" > app.py
git add app.py
git commit -qm "the code"
BASE=$(git rev-parse HEAD)

# state as an ORPHAN commit on a non-branch ref
TREE=$(printf 'READY_FOR_REVIEW\n' | git hash-object -w --stdin \
  | xargs -I{} sh -c 'printf "100644 blob {}\tstate\n" | git mktree')
STATE=$(git commit-tree "$TREE" -m "task SA-0099 -> READY_FOR_REVIEW")
git update-ref refs/saffron/tasks/SA-0099 "$STATE"
echo "base commit:  $BASE"
echo "state commit: $STATE"
cd ..

# --- the bare mirror the cell clones from ---------------------------------
git clone -q --mirror origin.git-src mirror.git
echo
echo "== refs present in the mirror =="
git --git-dir=mirror.git for-each-ref --format='  %(refname)'

# --- the cell's seed, verbatim from worktree.py ---------------------------
mkdir work && cd work
git init -q
git remote add origin "$ROOT/mirror.git"
git fetch -q origin
git checkout -q -b saffron/SA-0099 "$BASE"
git remote remove origin

echo
echo "== refs the CELL can see =="
git for-each-ref --format='  %(refname)' | sed 's/^$/  (none)/'
test -n "$(git for-each-ref)" || echo "  (no refs at all)"

echo
echo "== can the cell reach the state COMMIT object? =="
if git cat-file -e "$STATE" 2>/dev/null; then
  echo "  LEAK: state commit object is present in the cell"
else
  echo "  ok: state commit object absent from the cell"
fi

echo
echo "== can the cell reach the state ref by name? =="
if git rev-parse --verify -q refs/saffron/tasks/SA-0099 >/dev/null; then
  echo "  LEAK: ref is present"
else
  echo "  ok: ref absent"
fi

echo
echo "== what a plain clone of the mirror brings =="
cd "$ROOT"
git clone -q mirror.git plain
git --git-dir=plain/.git for-each-ref --format='  %(refname)' | head -20
echo "  -- state commit reachable in a plain clone?"
if git --git-dir=plain/.git cat-file -e "$STATE" 2>/dev/null; then
  echo "     yes (present)"
else
  echo "     no (absent)"
fi

echo
echo "== does a default git fetch in the plain clone bring it? =="
cd plain
git fetch -q origin
if git rev-parse --verify -q refs/saffron/tasks/SA-0099 >/dev/null; then
  echo "  ref arrived via default fetch"
else
  echo "  ok: default fetch ignored refs/saffron/* (collaborator unaffected)"
fi
echo
echo "root kept for inspection: $ROOT"
