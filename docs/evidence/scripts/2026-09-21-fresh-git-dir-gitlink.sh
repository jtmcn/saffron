#!/bin/sh
# Item 103, SA-0118: a gitlink a committed .gitmodules ignores, from a fresh dir.
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
echo one > a.txt
git add a.txt
git commit -qm base
B=$(git rev-parse HEAD)
printf '[submodule "sub"]\n\tpath = vendor/sub\n\turl = ./sub\n\tignore = all\n' > .gitmodules
git add .gitmodules
git update-index --add --cacheinfo "160000,1111111111111111111111111111111111111111,vendor/sub"
git commit -qm sub
H=$(git rev-parse HEAD)
git init -q --bare --template= "$T/clean"
echo "$PWD/.git/objects" > "$T/clean/objects/info/alternates"
echo "fresh dir name-only, ignore-submodules=none:"
git --git-dir="$T/clean" diff --ignore-submodules=none --name-only "$B" "$H"
echo "fresh dir name-only, no flag:"
git --git-dir="$T/clean" diff --name-only "$B" "$H"
rm -rf "$T"
