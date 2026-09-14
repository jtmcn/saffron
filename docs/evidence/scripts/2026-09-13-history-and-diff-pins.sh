#!/bin/sh
# Backlog items 110 and 89: what moves worktree.py's reads, and what pins them.
# Every read goes through _git's own -c overrides; diffs add DIFF_FLAGS.
# Run 2026-09-13 on the host (git 2.54) and in saffron/cell:saffron (2.39.5):
#   sh this.sh                                          # host
#   container run --rm -i saffron/cell:saffron sh -s < this.sh
# Both printed the same table. Results are in SA-0082 and SA-0083.
set -u
T=${TMPDIR:-/tmp}
G="git -c core.quotePath=false -c diff.suppressBlankEmpty=false -c core.useReplaceRefs=false -c core.bigFileThreshold=2g -c core.attributesFile=/dev/null"
DF="--src-prefix=a/ --dst-prefix=b/ --no-ext-diff --no-textconv --no-renames --abbrev=7 --unified=3 --diff-algorithm=myers"
echo "git: $(git --version)"

fresh() {
  d=$(mktemp -d) && cd "$d" && git init -q && git config user.email p@p && git config user.name p
}

# item 110: base, a commit touching a forbidden path, an innocent commit
hist() {
  fresh
  echo a > a.txt && git add . && git commit -qm base && BASE=$(git rev-parse HEAD)
  mkdir secret && echo s > secret/f.txt && git add . && git commit -qm "touch forbidden" && X=$(git rev-parse HEAD)
  echo b > b.txt && git add . && git commit -qm innocent && Y=$(git rev-parse HEAD)
}
reads() { # label, then env assignments for the reads
  label=$1; shift
  c=$(env "$@" $G rev-list --count "$BASE..HEAD" 2>"$T/probe.err" | tail -1)
  s=$(env "$@" $G log --format=%s "$BASE..HEAD" 2>>"$T/probe.err" | tr '\n' '|')
  n=$(env "$@" $G diff --name-only $DF "$BASE..HEAD" 2>>"$T/probe.err" | tr '\n' ' ')
  e=$(grep -v '^$' "$T/probe.err" | head -1 | cut -c1-50)
  printf '%-40s count=%-2s subjects=%-30s names=%s %s\n' "$label" "$c" "$s" "$n" "${e:+[stderr: $e]}"
}

echo "== 110: grafts"
hist; reads "no graft"
mkdir -p .git/info && echo "$Y $BASE" > .git/info/grafts
reads "info/grafts: head -> base"
reads "  + GIT_NO_REPLACE_OBJECTS=1" GIT_NO_REPLACE_OBJECTS=1
reads "  + GIT_GRAFT_FILE=/dev/null" GIT_GRAFT_FILE=/dev/null
reads "  + GIT_GRAFT_FILE=/nonexistent" GIT_GRAFT_FILE=/nonexistent

echo "== 110: shallow"
hist; echo "$Y" > .git/shallow
reads ".git/shallow: head"
reads "  + GIT_SHALLOW_FILE=/dev/null" GIT_SHALLOW_FILE=/dev/null
reads "  + GIT_GRAFT_FILE=/dev/null alone" GIT_GRAFT_FILE=/dev/null
printf '%-40s %s\n' "  + git --shallow-file=/dev/null" "$(git --shallow-file=/dev/null rev-list --count HEAD 2>&1 | head -1)"
hist; echo "$X" > .git/shallow
reads ".git/shallow: below the range"

echo "== 110: both pins"
hist; reads "clean repo" GIT_GRAFT_FILE=/dev/null GIT_SHALLOW_FILE=/dev/null
hist; mkdir -p .git/info && echo "$Y $BASE" > .git/info/grafts && echo "$Y" > .git/shallow
reads "grafts + shallow, no pins"
reads "grafts + shallow, both pins" GIT_GRAFT_FILE=/dev/null GIT_SHALLOW_FILE=/dev/null
printf '%-40s [%s]\n' "hint silenced by advice.graftFileDeprecated" \
  "$(env GIT_GRAFT_FILE=/dev/null git -c advice.graftFileDeprecated=false rev-list --count HEAD 2>&1 >/dev/null)"

# item 89: three settings, each against its candidate pin
echo "== 89: diff.interHunkContext"
fresh; seq 1 40 > n.txt && git add . && git commit -qm base && B=$(git rev-parse HEAD)
sed -i.bak -e 's/^5$/five/' -e 's/^14$/fourteen/' n.txt && rm n.txt.bak && git commit -qam edit
h() { printf '%-40s hunks=%s\n' "$1" "$(eval "$2" | grep -c '^@@')"; }
h "default" "$G diff $DF $B..HEAD"
git config diff.interHunkContext 10
h "diff.interHunkContext=10" "$G diff $DF $B..HEAD"
h "  + --inter-hunk-context=0" "$G diff $DF --inter-hunk-context=0 $B..HEAD"
h "  + -c diff.interHunkContext=0" "$G -c diff.interHunkContext=0 diff $DF $B..HEAD"

echo "== 89: color"
esc=$(printf '\033')
col() { printf '%-40s lines with escapes=%s\n' "$1" "$(eval "$2" | grep -c "$esc")"; }
col "default (pipe)" "$G diff $DF $B..HEAD"
git config color.ui always
col "color.ui=always" "$G diff $DF $B..HEAD"
col "  name-only" "$G diff --name-only $DF $B..HEAD"
col "  + --no-color" "$G diff $DF --no-color $B..HEAD"
git config color.diff always
col "color.diff=always too" "$G diff $DF $B..HEAD"
col "  + --no-color" "$G diff $DF --no-color $B..HEAD"
col "  + -c color.ui=never" "$G -c color.ui=never diff $DF $B..HEAD"

echo "== 89: diff.ignoreSubmodules"
fresh; echo a > a.txt && git add . && git commit -qm base && B=$(git rev-parse HEAD)
git update-index --add --cacheinfo 160000,"$B",vendor/sub && git commit -qm gitlink
sm() { printf '%-40s %s\n' "$1" "$(eval "$2" | tr '\n' ' ')"; }
sm "default" "$G diff --name-only $DF $B..HEAD"
git config diff.ignoreSubmodules all
sm "diff.ignoreSubmodules=all" "$G diff --name-only $DF $B..HEAD"
sm "  patch headers" "$G diff $DF $B..HEAD | grep -c '^diff --git'"
sm "  + --ignore-submodules=none" "$G diff --name-only $DF --ignore-submodules=none $B..HEAD"
sm "  + -c diff.ignoreSubmodules=none" "$G -c diff.ignoreSubmodules=none diff --name-only $DF $B..HEAD"
