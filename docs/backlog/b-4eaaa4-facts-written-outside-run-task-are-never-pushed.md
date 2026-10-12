---
id: b-4eaaa4
title: "Facts written outside `run_task` reach the mirror and are never pushed, so a discarded host loses them"
status: open
tier: 1
filed: 2026-10-12
specs: []
prs: []
commits: []
cites: []
related: [170]
---

## Problem

Found by the spec review of `SA-0278`, the spec that wires the record in.

`SA-0278` pushes a task's ref once, as `run_task` ends. Several writers append
facts after that, or with no `run_task` at all.

- `stack_layer`, from the stack batch (`saffron/batch.py:497`).
- `end_review`, from the stack's end review (`saffron/end_review.py:358`,
  `saffron/cli.py:697`).
- `stack_finish`, from the finishing layer (`saffron/finish.py:415`).
- `qualification`, from the qualify step (`saffron/qualify.py:169`).
- Every fact of a `saffron draft` task, which never reaches `run_task`
  (`saffron/cli.py:1226`).
- `reconcile`'s review states, `MERGED` among them.

Each lands in the mirror and stays there. ADR 10 says the record on
`refs/saffron/*` lets a host VM be discarded
(`docs/adr/0010-saffron-ships-as-an-engine-each-operator-deploys.md:126-127`).
That promise is not met while these facts live on one host only.

## Done looks like

Every fact a command writes reaches its repo's origin before the command
exits, or the command says which task's ref it could not push. A test drives
each writer above.

## Record

- 2026-10-12: filed from `SA-0278`'s spec review, round 1.
