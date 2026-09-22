#!/bin/sh
# Does GIT_DEFAULT_HASH make `git init --bare` create a sha256 dir? Item 103, SA-0118.
# Run 2026-09-21 on git 2.54 and 2.39.5 (saffron/cell-base:python): sha256, then
# sha1 with --object-format=sha1, on both.
set -eu
T=$(mktemp -d)
export HOME="$T/h" XDG_CONFIG_HOME="$T/x" GIT_CONFIG_NOSYSTEM=1
mkdir -p "$HOME" "$XDG_CONFIG_HOME"
git --version
GIT_DEFAULT_HASH=sha256 git init -q --bare "$T/a"
echo "GIT_DEFAULT_HASH=sha256: $(git --git-dir="$T/a" rev-parse --show-object-format)"
GIT_DEFAULT_HASH=sha256 git init -q --bare --object-format=sha1 "$T/b"
echo "same, with --object-format=sha1: $(git --git-dir="$T/b" rev-parse --show-object-format)"
rm -rf "$T"
