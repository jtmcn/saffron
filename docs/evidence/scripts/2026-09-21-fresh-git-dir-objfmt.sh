#!/bin/sh
# Item 103, SA-0118: a global init.defaultObjectFormat against the fresh dir.
# Run 2026-09-21: git 2.54 makes a sha256 dir and the diff fails, git 2.39.5
# (saffron/cell-base:python) ignores the key. --object-format fixes both.
set -eu
T=$(mktemp -d)
export HOME="$T/h" XDG_CONFIG_HOME="$T/x" GIT_CONFIG_NOSYSTEM=1
mkdir -p "$HOME" "$XDG_CONFIG_HOME"
echo "git: $(git --version)"
cd "$T"
git init -q r
cd r
git config user.email p@p
git config user.name p
printf 'a\n' > f.py
git add f.py
git commit -qm base
B=$(git rev-parse HEAD)
printf 'a\nb\n' > f.py
git commit -qam head
H=$(git rev-parse HEAD)
git config --global init.defaultObjectFormat sha256
git init -q --bare --template= "$T/clean"
echo "$T/r/.git/objects" > "$T/clean/objects/info/alternates"
echo "fresh dir format: $(git --git-dir="$T/clean" rev-parse --show-object-format)"
git --git-dir="$T/clean" diff --no-color "$B" "$H" 2>&1 | head -3 || true
rm -rf "$T/clean"
git init -q --bare --template= --object-format="$(git rev-parse --show-object-format)" "$T/clean"
echo "$T/r/.git/objects" > "$T/clean/objects/info/alternates"
echo "with --object-format from the worktree:"
git --git-dir="$T/clean" diff --no-color "$B" "$H" | grep '^+b' || true
rm -rf "$T"
