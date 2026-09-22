#!/bin/sh
# A committed .gitattributes, and a genuine binary, read from the worktree's
# git dir and from a fresh bare dir borrowing its objects. Item 103, SA-0118.
# Run 2026-09-21 on git 2.54 and 2.39.5 (saffron/cell-base:python), same output.
set -eu
T=$(mktemp -d)
export HOME="$T/h" XDG_CONFIG_HOME="$T/x" GIT_CONFIG_NOSYSTEM=1
mkdir -p "$HOME" "$XDG_CONFIG_HOME"
G="git -c core.bigFileThreshold=2g -c core.attributesFile=/dev/null"
echo "git: $(git --version)"
cd "$T"
git init -q r
cd r
git config user.email p@p
git config user.name p
printf 'a\n' > f.py
printf 'x\000y\n' > bin.dat
git add f.py bin.dat
git commit -qm base
B=$(git rev-parse HEAD)
echo '*.py -diff' > .gitattributes
printf 'a\nb\n' > f.py
printf 'x\000z\n' > bin.dat
git add -A
git commit -qm head
H=$(git rev-parse HEAD)
git init -q --bare --template= "$T/clean"
echo "$T/r/.git/objects" > "$T/clean/objects/info/alternates"
echo "worktree git dir:"
$G diff --no-color --full-index "$B" "$H" | grep -E '^(\+b|Binary)' || true
echo "fresh git dir:"
$G --git-dir="$T/clean" diff --no-color --full-index "$B" "$H" | grep -E '^(\+b|Binary)' || true
echo "fresh git dir, name-only:"
$G --git-dir="$T/clean" diff --name-only "$B" "$H"
echo "fresh git dir, HEAD unresolved:"
$G --git-dir="$T/clean" rev-parse HEAD 2>&1 || true
echo "fresh git dir, a worktree whose .git is a file:"
rm -rf "$T/clean"
rm -rf "$T/r"
