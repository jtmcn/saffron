---
id: b-4e1b6d
title: "`saffron watch` shows nothing while a stack batch reviews or writes a spec, because those sessions log no events"
status: open
tier: 2
filed: 2026-10-05
specs: []
prs: []
commits: []
cites: [§4.3]
related: [b-2d09de]
---

## Problem

Found by the operator during the first live `saffron batch --stack`, on
2026-10-05.

A stack batch reviews each spec in a cell before that spec's own cell runs.
`_stack_review` in `saffron/cli.py` binds `implement.run_agent` with no
`emit`. So `run_agent` keeps its default, `print(describe(event))`, and every
event of the session goes to the batch's stdout alone. No `EventLog` writes
an `events.jsonl` for it. The session's checkout sits at
`~/.saffron/batches/v0/spec-review/SA-NNNN`, which holds no log.

`saffron watch` follows `events.jsonl` under the batch tree. It printed
nothing for the first several minutes of the night, while `SA-0208`'s spec
review ran 377 agent lines into the batch log. The operator read that as
`watch` not working with a batch. The spec-writing session that
`_stack_revise` binds looks the same.

## Done looks like

`saffron watch` with no spec id shows a spec review or a spec-writing
session as it runs, beside the cells. Each line names its phase. A test drives a stack batch's review session and reads its
events back through the follower.

## Record

- 2026-10-05: filed during stage 2's first stack batch, at the operator's
  request.
- 2026-10-08: recurred in the spec loop's run 31. The spec review wrote to
  `batches/v0/spec-review/SA-NNNN/` with no task folder. So cell-watch kept
  following the last loop's task, and its first hand-over named SA-0224.
  The review's route was read from `spec_reviews` in the ledger by hand.
