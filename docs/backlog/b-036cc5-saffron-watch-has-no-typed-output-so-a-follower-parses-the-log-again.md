---
id: b-036cc5
title: "`saffron watch` has no typed output, so a follower outside Python parses `events.jsonl` a second time"
status: partial
tier: 3
filed: 2026-10-07
by_hand: true
specs: []
prs: [1076]
commits: []
cites: []
related: [b-2d09de, b-4e1b6d, b-ba0cba]
---

## Problem

Found by the `cell-watch` mod spike on 2026-10-07.

`saffron/watch.py` adds no second parser and no second formatter. It reads
the log through `read_log_since` and renders each event through `describe`.
That rule holds only inside Python. The mod in `.claude/skills/cell-watch/`
runs in Claude Code's TypeScript host, so it parses each line again. It also
picks its own newest task and renders its own lines.

`saffron watch` prints only rendered text. A follower in another language
must choose between a second parser and a pattern over rendered lines. The spec
loop's Monitor took the second path. Its pattern needs anchoring, because an
agent line that quoted `SCOPE_REVIEW` once fired it.

## Done looks like

`saffron watch --json` prints one object per event: the event as `read_log`
typed it, and the line `describe` renders for it. It keeps the newest-task
default and the noise filter. The `cell-watch` mod then reads that stream and
drops `hooks/progress.ts`'s parser.

## Record

- 2026-10-07: filed from the `cell-watch` mod spike.
- 2026-11-08: partial by hand. `follow` and `follow_every_task` take `as_json`, and each yields one object per event with its `event` and `line`. Left: the `--json` flag in `saffron/cli.py`, which a queued spec touches, and the `cell-watch` mod reading that stream in place of its own parser.
