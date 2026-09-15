---
id: 109
title: A mutant its witness survives is spelled out to the implementer in the repair turn
status: done
tier: 1
filed: 2026-09-12
closed: 2026-09-14
specs: [SA-0078]
prs: [243]
commits: []
cites: []
related: [80, 114]
---

## Problem

Found 2026-09-12 while deciding item 80. `witness_gate` builds the
`survived-mutant` failure with a message quoting the mutant's `find`, its
`replace` and its file (`saffron/gates/core/witness.py`). At `elevated`,
`witness_blocking` makes that failure blocking, and `repair_prompt` renders
every blocking new failure's `code` and `message` to the implementer verbatim.
So the first attempt whose witness survives hands the next attempt the exact
edit it is judged by. That is the test written to kill a known edit, the thing
`witness` exists to refuse, delivered by `witness` itself.

Below `elevated`, `witness` is advisory and its failures never reach the repair
turn, and no gate summary reaches any prompt. The message is the one path. It is
filed apart from item 80 and ahead of it because every place 80 might store a
mutant is undone by this.

## Done looks like

the message naming
the criterion's claim and its witness and
carrying neither `find` nor `replace`, with a witness that asserts over the
whole gate result. The pull request body loses the edit with it. That is
intended: the operator has the spec.

## Record

**Status: merged, 2026-09-14 — `SA-0078`, PR #243, in stack #251.** The mutant that does not apply still reaches the critic: item 114.
