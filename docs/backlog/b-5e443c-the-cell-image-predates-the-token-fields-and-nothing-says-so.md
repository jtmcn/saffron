---
id: b-5e443c
title: The cell image predates `agent_runner.py`'s token fields, so no event log carries a token count and nothing says why
status: open
tier: 2
filed: 2026-09-19
specs: []
prs: []
commits: []
cites: [§4.1, §5.1.2]
related: [146, 147, 10]
---

## Problem

Found in the spec loop's run 8, 2026-09-19. The operator asked whether time
and tokens are recorded per step.

Time, turns and cost are recorded: attempt rows, `gate_results.duration_ms`
and every event's timestamp. Tokens are not.

`SA-0090` (#278, merged 2026-09-16) added the usage fields to
`images/agent_runner.py:24-37`. That file reaches a cell only through
`saffron/cell-base:python` (`images/cell-base.python.Dockerfile:57`), which is
built by hand. `.saffron/Dockerfile:3` builds the repo's image `FROM` it. The
base on this host was built 2026-08-29. So every run-8 cell ran the old runner.
`grep -c input_tokens` finds zero in each of `~/.saffron/batches/v0/SA-0101` to
`SA-0108`'s `events.jsonl`.

Three gaps:

- Nothing compares the image's `agent_runner.py` with the checkout's. A stale
  runner reads the same as a runner that reports no usage.
- The ledger has no token column, so even a fresh image records tokens only in
  the event log (items 146 and 147).
- `CLAUDE.md` says to rebuild the base after editing it, and nothing checks
  that anyone did.

## Done looks like

Preflight compares a hash of the image's `/opt/saffron/agent_runner.py` with
the checkout's `images/agent_runner.py`. A mismatch fails preflight and names
the rebuild command. Token counts per attempt reach the ledger, or a recorded
decision says the event log is their only home.

## Record

- 2026-09-19: filed from the spec loop's run 8 (stack #351 ← #360 ← #355 ←
  #366 ← #353).
