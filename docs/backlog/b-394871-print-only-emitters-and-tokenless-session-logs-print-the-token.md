---
id: b-394871
title: Print-only emitters and tokenless session logs still print the cell's token
status: open
tier: 2
filed: 2026-11-21
specs: []
prs: []
commits: []
cites: [§5.7]
related: [b-0f5493]
---

## Problem

Found by `SA-0421`'s spec writer and both its reviews.

`SA-0421` prints an `Agent` event's line from the event its log redacted.
Two kinds of emitter stay outside it.

- `_spec_session_emit` (`saffron/cli.py:1370-1375`) builds an `EventLog`
  with no token. A spec review, a spec writer, an end review and a
  follow-up writer each emit through it under `saffron batch`. So their
  lines redact the listed shapes, and the cell's own token prints whole.
- `saffron review` (`saffron/commit_review.py:295`) and `saffron draft`
  (`saffron/cli.py:1700-1704`, through `run_agent`'s default) print each
  line as it came. Neither holds a log.

## Done looks like

Each session log `_spec_session_emit` builds is handed the token its
session holds. Each print-only emitter redacts the listed shapes and the
token before it prints. A test drives one of each kind with an `Agent`
event that carries both, and asserts neither reaches stdout.

## Record

- 2026-11-21: filed with `SA-0421`, which kept both out of scope.
