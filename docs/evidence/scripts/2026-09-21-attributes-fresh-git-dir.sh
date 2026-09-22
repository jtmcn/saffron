#!/bin/sh
# Backlog item 103: two attribute sources no flag or -c override reaches.
# A diff read from a fresh bare git dir that borrows the objects escapes both.
# Run 2026-09-21 on the host (git 2.54) and in saffron/cell-base:python (2.39.5):
#   sh this.sh
#   container run --rm -i saffron/cell-base:python sh -s < this.sh
# Both printed the same table.
set -eu
T=$(mktemp -d)
# XDG_CONFIG_HOME too: with HOME moved, `config --global` writes the XDG file.
export HOME="$T/home" XDG_CONFIG_HOME="$T/xdg" GIT_CONFIG_NOSYSTEM=1
mkdir -p "$HOME" "$XDG_CONFIG_HOME"
G="git -c core.bigFileThreshold=2g -c core.attributesFile=/dev/null"
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

show() {
  if $G "$@" diff --no-color "$B" "$H" | grep -q '^+b$'; then
    echo "  hunks"
  else
    echo "  Binary files differ"
  fi
}

clean() {
  rm -rf "$T/clean"
  git init -q --bare "$@" "$T/clean"
  echo "$T/r/.git/objects" > "$T/clean/objects/info/alternates"
}

echo '* -diff' > .git/info/attributes
echo "info/attributes, the worktree's git dir:"
show
echo "info/attributes, a fresh git dir:"
clean
show --git-dir="$T/clean"
rm .git/info/attributes

echo '* -diff' > .gitattributes
echo .gitattributes >> .git/info/exclude
echo "untracked excluded .gitattributes, the worktree's git dir:"
show
echo "untracked excluded .gitattributes, a fresh git dir:"
clean
show --git-dir="$T/clean"

# The agent writes ~/.gitconfig, so init.templateDir can seed the fresh dir.
mkdir -p "$HOME/tpl/info"
echo '* -diff' > "$HOME/tpl/info/attributes"
git config --global init.templateDir "$HOME/tpl"
echo "templateDir seeding info/attributes, a fresh git dir:"
clean
show --git-dir="$T/clean"
echo "templateDir seeding info/attributes, a fresh git dir with --template=:"
clean --template=
show --git-dir="$T/clean"

rm -rf "$T"
