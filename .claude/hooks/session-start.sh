#!/usr/bin/env bash
# The spec loop names two skills it does not carry: `superpowers:requesting-code-review`
# (step 2d's reviewer) and `gh-stack` (authoritative on `link` vs `submit`). Both are
# installed on the host that wrote them and neither exists in a Claude Code on the web
# container: it starts from a fresh clone with `SKIP_PLUGIN_MARKETPLACE=true`, so the
# `enabledPlugins` above it are never fetched and `~/.claude` carries nothing. Install
# them here, before the session reads what skills it has.
#
# Web only, by `$CLAUDE_CODE_REMOTE`: a host already has both, and a second copy of
# gh-stack as a personal skill would collide with the plugin's.
#
# Nothing in here may end the session. `set -e` is deliberately absent, every network
# command is bounded by `timeout`, and a failure says what the loop will be missing on
# stderr and exits 0 — stdout belongs to the hook protocol, not to logging.
set -uo pipefail

[ "${CLAUDE_CODE_REMOTE:-}" = "true" ] || exit 0

# A plugin, not a loose skill directory: the loop writes the `superpowers:` prefix, and
# only an installed plugin answers to it. Installing the skill by hand would give a bare
# `requesting-code-review` that the name in SKILL.md does not reach.
if ! claude plugin list 2>/dev/null | grep -q 'superpowers@superpowers-dev'; then
  timeout 120 claude plugin marketplace add https://github.com/obra/superpowers >/dev/null 2>&1
  timeout 120 claude plugin install superpowers@superpowers-dev >/dev/null 2>&1 ||
    echo 'session-start: superpowers install failed — the spec loop step 2d has no reviewer skill' >&2
fi

# gh-stack ships its skill inside the extension's Go repository and is not a plugin, so
# it installs as a personal skill. Blobless and sparse: the skill is four files, the
# repository is 11MB of Go.
gh_stack="${HOME}/.claude/skills/gh-stack"
if [ ! -f "${gh_stack}/SKILL.md" ]; then
  tmp="$(mktemp -d)"
  if timeout 120 git clone --depth 1 --filter=blob:none --sparse -q \
       https://github.com/github/gh-stack "${tmp}/gh-stack" >/dev/null 2>&1 &&
     git -C "${tmp}/gh-stack" sparse-checkout set skills/gh-stack >/dev/null 2>&1 &&
     [ -f "${tmp}/gh-stack/skills/gh-stack/SKILL.md" ]; then
    mkdir -p "$(dirname "${gh_stack}")"
    cp -R "${tmp}/gh-stack/skills/gh-stack" "${gh_stack}"
  else
    echo 'session-start: gh-stack skill fetch failed — its reference in the spec loop is unreadable here' >&2
  fi
  rm -rf "${tmp}"
fi

exit 0
