---
id: b-8826cf
title: A rebuttal that adds a suppression ends its task EXHAUSTED, since REBUT gets no repair turn
status: open
tier: 2
filed: 2026-10-29
specs: []
prs: []
commits: []
cites: [§5.4, §5.6]
related: [b-92c92a]
---

## Problem

Found in the spec loop's run 50, on `SA-0325` in batch 59.

Attempt 1 was green. REVIEW raised three blockers, and REBUT fixed all
three. Its fix for the contract blocker put a closure inside a loop, and
ruff flagged B023 on ten lines. REBUT silenced each one with a `noqa`
comment. `integrity` counted ten new failures, and REBUT does not re-enter
the repair loop. The task ended `EXHAUSTED` at $18.23 of $20 on a diff
whose only defect was the suppressions.

The delegate moved the closure above the loop by hand (`2992c066`, #989).
That cleared B023 with no suppression, and `saffron adopt` re-gated it
green.

## Done looks like

A rebuttal whose only new failures are ones a repair turn could clear gets
that turn. Or REBUT's prompt says a suppression fails `integrity`, and a
measured run shows it no longer writes one.

## Record

- 2026-10-29: filed from the spec loop's run 50.
