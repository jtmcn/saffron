---
id: b-e880ac
title: Saffron takes the cell token from the environment of whoever starts it, so a delegate session must hold the credential first
status: open
tier: 2
filed: 2026-10-06
specs: []
prs: []
commits: []
cites: [§5.1]
related: []
---

## Problem

Raised by the operator on 2026-10-06, after stage 2 of the delegate-loop plan.

`CLAUDE_CODE_OAUTH_TOKEN` must reach cell agents and nothing else. A Claude
Code session started from the CLI, such as a delegate, must never have it
loaded. `DESIGN.md` §5.1 makes it the one credential a cell holds.

Saffron reads the token from its own process environment. `saffron/cli.py`
checks it at `:416` and passes `os.environ.get("CLAUDE_CODE_OAUTH_TOKEN")` at
`:495`, `:543`, `:585` and `:1549`. `saffron/preflight.py:464` and
`saffron/cell/session.py:820` read the same variable. So the process that
starts `saffron cell` or `saffron batch` must hold the token first.

When a delegate starts a batch, its session fetches the credential. In runs 28
and 29 it ran a `sed` over `~/.secrets` and wrote a key-only file. A
user-settings allow rule permits that line. The launchd plist sources
`~/.secrets` under `set -a` (`docs/HOST-HARDENING.md` §4a). Each path puts the
token in a process above Saffron. `driver.py jev` has the same shape for
`TYPESAFE_API_KEY` (`.claude/skills/run-saffron-spec-loop/driver.py:1225`).

## Done looks like

- The token lives in GCP Secret Manager, not in `~/.secrets`.
- Saffron fetches it through a command the host declares, such as
  `SAFFRON_CELL_TOKEN_COMMAND`. For this host that is
  `gcloud secrets versions access latest --secret=<name>`. Core names no
  secret store and runs no `gcloud` of its own. An undeclared command is an
  `auth` readiness failure, never a fallback.
- Saffron runs the command when it needs the token, and keeps the value in a
  local. It never writes it to `os.environ` or a log. It passes it only as the
  `env` argument of cell creation and to the proxy check.
- A delegate and the launchd job run `saffron batch` with no token in their
  environment. The `sed` allow rule goes, and deny rules cover `~/.secrets`
  and the secret's access command for Claude Code sessions.
- `driver.py jev` fetches `TYPESAFE_API_KEY` the same way, through its own
  declared command.
- Tests drive a batch started with an empty environment to readiness through
  the command. They assert the token appears in no gate's environment and no
  `events.jsonl`. A missing or failing command reads as `auth`.
- `CLAUDE.md`'s Commands section, `docs/HOST-HARDENING.md` §1a,
  `docs/HOST-HARDENING.md` §4a and `docs/host/dev.saffron.batch.plist` say
  the new way.

A deny rule is policy, not a boundary. The delegate can still start Saffron,
and its own `gcloud` login reaches the secret unless IAM denies it. If the delegate must be unable
to obtain the token, the token's holder runs as another principal. That is a
separate item.

## Record

- 2026-10-06: filed at the operator's request, after stage 2's batches.
  The operator chose GCP Secret Manager as the store.
