---
id: b-80cc6e
title: "The loop's driver, its `GOTCHAS.md` and ADRs 4 and 8 still name `REBUTTING` and `REVIEWING` as the halts"
status: open
tier: 2
filed: 2026-10-19
by_hand: true
specs: []
prs: []
commits: []
cites: [§5.5, §5.6]
related: [120, b-032c3e]
---

## Problem

Found by both seats on #903 and #913, in the spec loop's run 44.

`SA-0276` (#903) makes REBUT's halt write `REBUTTAL_UNJUDGED`. `SA-0287` (#913)
makes REVIEW's halt write `REVIEW_INCOMPLETE`. Each spec's Out of scope names
the texts below as hand edits once it lands.

- `.claude/skills/run-saffron-spec-loop/driver.py:1018` holds a child back
  unless its parent is `READY_FOR_REVIEW`.
- `driver.py:1201` prints the generic halted-at line for either state.
  `driver.py:1100` cites a task left `REBUTTING` as the halt's shape.
- `GOTCHAS.md:69`, `:75` and `:159` describe the halt as `REBUTTING`.
- ADR 4 (`docs/adr/0004-the-critic-is-host-invoked-lenses-with-no-vote.md:42`)
  and ADR 8 (`docs/adr/0008-review-reads-each-hunk-against-the-standing-instructions.md:106`)
  say a lens that errors stops the task at `REVIEWING`.

By hand because `SA-0279` refuses a spec that touches `.claude/`, and the ADRs
are protected.

## Done looks like

The driver and `GOTCHAS.md` name both terminal states, and the record command
prints guidance for each. ADR 4 and ADR 8 name `REVIEW_INCOMPLETE`, with the
change dated in each.

## Record

- 2026-10-19: filed from the spec loop's run 44.
