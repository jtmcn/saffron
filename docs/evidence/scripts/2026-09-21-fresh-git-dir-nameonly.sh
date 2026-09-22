#!/bin/sh
# Item 103, SA-0118: the name-only listing under both attribute vectors.
# Run 2026-09-21 on git 2.54 and 2.39.5 (saffron/cell-base:python), same output.
set -eu
T=$(mktemp -d)
export HOME="$T/h" XDG_CONFIG_HOME="$T/x" GIT_CONFIG_NOSYSTEM=1
mkdir -p "$HOME" "$XDG_CONFIG_HOME"
cd "$T"
git init -q r
cd r
git config user.email p@p
git config user.name p
printf 'a\n' > f.py
git add f.py
git commit -qm b
B=$(git rev-parse HEAD)
printf 'a\nb\n' > f.py
git commit -qam h
echo '* -diff' > .git/info/attributes
echo "info/attributes name-only:"
git diff --name-only "$B" HEAD
rm .git/info/attributes
echo '* -diff' > .gitattributes
echo .gitattributes >> .git/info/exclude
echo "excluded .gitattributes name-only:"
git diff --name-only "$B" HEAD
echo "status:"
git status --porcelain --untracked-files=all
echo end
rm -rf "$T"
