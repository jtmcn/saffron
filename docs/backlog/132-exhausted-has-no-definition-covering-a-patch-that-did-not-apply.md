---
id: 132
title: EXHAUSTED has no definition covering a patch that did not apply, and its reason misdescribes an empty one
status: open
tier: 3
filed: 2026-09-15
by_hand: true
specs: [SA-0087]
prs: [274]
commits: []
cites: [§3.3, §5.5]
related: [118]
---

## Problem

**Tier 3.** Found reviewing `SA-0087` (PR #274).

`CONTEXT.md` §6 defines `EXHAUSTED` as *a task that could not pass its own gates
within `max_attempts`*, and `DESIGN.md` §3.3's arrow names two ways in: the
budget stop, and four attempts still red. `SA-0087` adds a third — the exported
patch did not apply in the critic cell, or applied and could not be committed —
and `DESIGN.md` §5.5 mandates it. `GATE_ERROR`'s arrow was widened for the
critic cell's binary case in the same revision; `EXHAUSTED`'s was not.

`CONTEXT.md` is authoritative for what the words mean, and both it and
`DESIGN.md` are `forbidden` in `SA-0087`, so the code now reaches a state its own
definition does not describe.

Second, smaller half: an attempt whose commits net to an empty diff passes the
only doneness check there is (`commits == 0`), and now dies in the critic cell —
`printf '' | git apply` gives `error: No valid patches in input`, no
`_NO_FULL_INDEX` marker, so it ends `EXHAUSTED` reading *"the exported patch did
not apply in the critic cell"*. The state is defensible; the reason misdescribes
what happened, and §4.3 is the standing rule that doneness is measured rather
than reported.

## Done looks like

`CONTEXT.md` §6's `EXHAUSTED` entry and `DESIGN.md` §3.3's arrow naming the
critic cell's apply as a third way in, and a distinct reason for an export that
carried no patch at all.
